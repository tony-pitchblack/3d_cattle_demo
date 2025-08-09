# addon_camera_crosshair_cut.py
# Install: Edit → Preferences → Add-ons → Install… (this file) → Enable
# Use: Select a camera and a mesh (any order; mesh may be hidden) → Ctrl+F (Object Mode)
# Or: F3 → "Crosshair Cut (Copy)"
# Result: Duplicates the mesh, hides the original, cuts the copy by the camera’s crosshair.
# Naming: "<orig>.cut_<camera>"

bl_info = {
    "name": "Camera Crosshair Cut (Copy)",
    "author": "you",
    "version": (1, 0, 1),
    "blender": (4, 0, 0),
    "location": "3D View > Object menu / Search",
    "description": "Create per-camera hidden crosshair planes and cut a COPY of a mesh along them; original is hidden",
    "category": "Object",
}

import bpy
from mathutils import Vector

_addon_kms = []  # keymap handles


# ------------------------------- utilities -----------------------------------

def _ensure_object_mode():
    obj = bpy.context.object
    if obj and obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def _safe_hide(obj, viewport=True, render=True):
    try:
        obj.hide_set(viewport)
    except Exception:
        obj.hide_viewport = viewport
    obj.hide_render = render


def _link_like_original(new_obj, ref_obj):
    users = getattr(ref_obj, "users_collection", None) or []
    if users:
        for c in users:
            if new_obj.name not in c.objects:
                c.objects.link(new_obj)
    else:
        bpy.context.scene.collection.objects.link(new_obj)


def _is_descendant(child, ancestor):
    p = child.parent
    while p:
        if p == ancestor:
            return True
        p = p.parent
    return False


def _is_plane_like(o):
    return o.type == 'MESH' and ('plane' in o.name.lower() or len(o.data.polygons) <= 2)


def _qualifies_as_target(o, cam):
    return (
        o and o.type == 'MESH'
        and not _is_plane_like(o)
        and not o.get("is_cutter_plane", False)
        and not _is_descendant(o, cam)
    )


def _plane_from_object(obj):
    p = obj.matrix_world.to_translation()
    n = (obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
    return p, n


def _bisect_keep(obj, plane_point, plane_normal, keep_positive_side: bool):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(
        plane_co=plane_point,
        plane_no=plane_normal,
        use_fill=True,
        clear_inner=not keep_positive_side,   # drop -normal side if keeping +
        clear_outer=keep_positive_side,       # drop +normal side if keeping -
    )
    bpy.ops.object.mode_set(mode='OBJECT')


def _order_cutters(objs):
    def tag(o):
        n = o.name.lower()
        if "horizontal" in n:
            return (0, n)
        if "vertical" in n:
            return (1, n)
        return (2, n)
    return sorted(objs, key=tag)


def _mid(a, b):
    return (a + b) * 0.5


def _normals_camspace(cam):
    # Shift-aware (aspect/Fit/Shift handled); Blender 4.5+ requires keyword 'scene='
    tl, tr, br, bl = cam.data.view_frame(scene=bpy.context.scene)
    top_mid = _mid(tl, tr)
    bot_mid = _mid(bl, br)
    left_mid = _mid(tl, bl)
    right_mid = _mid(tr, br)
    n_v = top_mid.cross(top_mid - bot_mid).normalized()          # vertical guide
    n_h = right_mid.cross(right_mid - left_mid).normalized()     # horizontal guide
    return n_h, n_v


def _orient_to_cam_normal(obj, cam, n_cam):
    n_world = (cam.matrix_world.to_3x3() @ n_cam).normalized()
    z = Vector((0, 0, 1))
    obj.rotation_euler = z.rotation_difference(n_world).to_euler()


def _link_exclusively(obj, target_coll):
    # unlink everywhere, then link only to target_coll (prevents “shadowing”)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    if obj.name not in target_coll.objects:
        target_coll.objects.link(obj)


def _get_or_adopt_plane(name, cam, fallbacks):
    o = bpy.data.objects.get(name)
    if o and o.type == 'MESH':
        return o
    # adopt legacy-named plane if it's already parented to THIS camera
    for fb in fallbacks:
        p = bpy.data.objects.get(fb)
        if p and p.type == 'MESH' and p.parent == cam:
            p.name = name
            return p
    # create new plane at camera
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=cam.location)
    o = bpy.context.object
    o.name = name
    return o


# --------------------------------- operator ----------------------------------

class VIEW3D_OT_camera_crosshair_cut(bpy.types.Operator):
    """Create per-camera hidden crosshair planes (shift-aware) and cut a COPY of a mesh along them"""
    bl_idname = "view3d.camera_crosshair_cut"
    bl_label = "Crosshair Cut (Copy)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _ensure_object_mode()

        sel = list(context.selected_objects)
        active = context.view_layer.objects.active

        # ---- camera pick (order-agnostic) ----
        cam = None
        if active and active.type == 'CAMERA':
            cam = active
        else:
            cams = [o for o in sel if o.type == 'CAMERA']
            cam = cams[0] if cams else context.scene.camera

        if not cam:
            self.report({'ERROR'}, "No camera found. Select a camera or set the scene camera.")
            return {'CANCELLED'}

        # ---- target pick (works if hidden / any order) ----
        candidates_sel = [o for o in sel if _qualifies_as_target(o, cam)]
        target = candidates_sel[0] if len(candidates_sel) == 1 else None
        if target is None and active and _qualifies_as_target(active, cam):
            target = active
        if target is None:
            all_candidates = [o for o in context.scene.objects if _qualifies_as_target(o, cam)]
            if len(all_candidates) == 1:
                target = all_candidates[0]

        if target is None:
            self.report({'ERROR'}, "Could not determine a unique target mesh. Select it (any order) "
                                   "or leave only one qualifying mesh in the scene.")
            return {'CANCELLED'}

        orig_name = target.name

        # ---- create/refresh per-camera planes ----
        name_h = f"{cam.name}.Plane.cutter.horizontal"
        name_v = f"{cam.name}.Plane.cutter.vertical"

        ph = _get_or_adopt_plane(name_h, cam, ("Plane.cutter.horizontal",))
        pv = _get_or_adopt_plane(name_v, cam, ("Plane.cutter.vertical",))

        for o in (ph, pv):
            o.location = cam.location
            o.scale = (1000.0, 1000.0, 1000.0)
            o.parent = cam
            o.matrix_parent_inverse = cam.matrix_world.inverted()
            o["is_cutter_plane"] = True
            target_coll = cam.users_collection[0] if cam.users_collection else context.scene.collection
            _link_exclusively(o, target_coll)
            _safe_hide(o, True, True)

        n_h_cam, n_v_cam = _normals_camspace(cam)
        _orient_to_cam_normal(ph, cam, n_h_cam)
        _orient_to_cam_normal(pv, cam, n_v_cam)

        cutters = _order_cutters([o for o in cam.children_recursive if o.get("is_cutter_plane")])
        if not cutters:
            self.report({'ERROR'}, f"No cutter planes on '{cam.name}'.")
            return {'CANCELLED'}

        # ---- duplicate target, hide original, cut the copy ----
        work = target.copy()
        work.data = target.data.copy()
        work.name = f"{orig_name}.cut_{cam.name}"
        _link_like_original(work, target)
        _safe_hide(target, True, True)     # original invisible
        _safe_hide(work, False, False)     # copy visible

        current = [work]
        for cutter in cutters:
            p, n = _plane_from_object(cutter)
            nxt = []
            for src in current:
                pos = src.copy(); pos.data = src.data.copy(); _link_like_original(pos, src)
                neg = src.copy(); neg.data = src.data.copy(); _link_like_original(neg, src)
                _bisect_keep(pos, p, n, True)
                _bisect_keep(neg, p, n, False)
                bpy.data.objects.remove(src, do_unlink=True)
                nxt += [pos, neg]
            current = nxt

        if not current:
            self.report({'ERROR'}, "Nothing to join after slicing (does the mesh intersect the planes?).")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        for o in current:
            o.select_set(True)
        context.view_layer.objects.active = current[0]
        bpy.ops.object.join()
        joined = context.view_layer.objects.active
        _safe_hide(joined, False, False)
        joined.name = f"{orig_name}.cut_{cam.name}"

        # optional seam cleanup
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.mesh.merge_by_distance(distance=1e-6)
        except Exception:
            pass
        bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, f"Created '{joined.name}'. Original '{orig_name}' hidden.")
        return {'FINISHED'}


# ------------------------------- UI integration ------------------------------

def menu_func(self, context):
    # Use idname string to avoid NameError at import
    self.layout.operator('view3d.camera_crosshair_cut', text="Crosshair Cut (Copy)")


# -------------------------------- register -----------------------------------

classes = (VIEW3D_OT_camera_crosshair_cut,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)

    # Hotkey: Ctrl+F in Object Mode
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
        kmi = km.keymap_items.new(
            'view3d.camera_crosshair_cut',
            type='F', value='PRESS', ctrl=True, shift=True
        )
        _addon_kms.append((km, kmi))


def unregister():
    # remove keymap
    for km, kmi in _addon_kms:
        km.keymap_items.remove(kmi)
    _addon_kms.clear()

    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

