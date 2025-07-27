# Set up remote rendering Flamenco server for remote gpu rendering

1. Install Flamenco on server according to docs
2. Create a shared directory to sync server render to client automatically

Assert permission for server user:
```bash
sudo chown bonting:bonting /home/bonting/3d_cattle_demo
```

# Set up remote repo data storage via sshd
On client create systemd oneshot unit that will mount your SSHFS share once at boot for user youruser. Place this file as /etc/systemd/system/mount-3d_cattle_demo.service:

```bash
[Unit]
Description=One-shot SSHFS mount for 3d_cattle_demo
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=youruser
# Ensure this directory exists and is owned by youruser before running:
#   sudo mkdir -p /home/youruser/3d_cattle_demo
#   sudo chown youruser:youruser /home/youruser/3d_cattle_demo
ExecStart=/usr/bin/sshfs \
  bonting@10.0.0.1:/home/bonting/3d_cattle_demo \
  /home/youruser/3d_cattle_demo \
  -o reconnect \
  -o ServerAliveInterval=15 \
  -o allow_other
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo mkdir -p /home/youruser/3d_cattle_demo
sudo chown youruser:youruser /home/youruser/3d_cattle_demo
sudo systemctl daemon-reload
sudo systemctl enable mount-3d_cattle_demo.service
sudo systemctl start  mount-3d_cattle_demo.service
```

# FAQ
## Failed push to HF repo
Make sure all commits use git lfs:
```bash
git lfs migrate import --include="*.FBX,*.obj,*.stl,*.exr,*.STEP,*.blend,*.blend1,*.fspy"
```

# Misc
## Blender MCP
Use Blender MCP for Cursor: https://github.com/ahujasid/blender-mcp