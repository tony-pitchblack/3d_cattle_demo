import bpy, os

# ——— user settings ———
cams    = ["Camera.front", "Camera.left"]
out_dir = bpy.path.abspath("//renders/depth_front_left")          # folder beside your .blend
os.makedirs(out_dir, exist_ok=True)

scene       = bpy.context.scene
view_layer  = scene.view_layers["ViewLayer"]
view_layer.use_pass_z = True                     # we need the Z pass

# ------------------------------------------------------------------
# ONE‑TIME compositor setup: Composite = Depth
# ------------------------------------------------------------------
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()

rlayers   = tree.nodes.new("CompositorNodeRLayers")
composite = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rlayers.outputs["Depth"], composite.inputs["Image"])

# ------------------------------------------------------------------
# helper: render once with the current scene settings
# ------------------------------------------------------------------
def render_to(path, file_fmt, color_mode="RGBA", color_depth="8"):
    scene.render.image_settings.file_format  = file_fmt
    scene.render.image_settings.color_mode   = color_mode
    scene.render.image_settings.color_depth  = color_depth
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

# ------------------------------------------------------------------
# LOOP cameras
# ------------------------------------------------------------------
for cam_name in cams:
    cam = bpy.data.objects.get(cam_name)
    if not cam or cam.type != 'CAMERA':
        print(f"[WARN] '{cam_name}' not found – skipped")
        continue

    scene.camera = cam

    # 1) RGB shot – compositor OFF
    scene.use_nodes = False
    rgb_path = os.path.join(out_dir, f"{cam_name}_rgb.png")
    render_to(rgb_path, "PNG", color_mode="RGBA", color_depth="8")
    print("RGB saved ⇒", rgb_path)

    # 2) Depth shot – compositor ON (Depth‑>Composite)
    scene.use_nodes = True
    depth_path = os.path.join(out_dir, f"{cam_name}_depth.exr")
    render_to(depth_path, "OPEN_EXR", color_mode="BW", color_depth="32")
    print("Depth saved ⇒", depth_path)

print("✓ All cameras rendered.")
