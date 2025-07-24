# Set up Flamenco server for remote gpu rendering

1. Install Flamenco on server according to docs
2. Create a shared directory to sync server render to client automatically

Assert permission for server user:
```bash
sudo chown bonting:bonting /home/bonting/3d_cattle_demo
```

On server use reverse ssh to mount via sshfs like:
```bash
sshfs \
  -p 2222 \
  -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,allow_other \
  anton@localhost:/home/anton/3d_cattle_demo \
  /home/bonting/3d_cattle_demo
```

# Misc
## Blender MCP
Use Blender MCP for Cursor: https://github.com/ahujasid/blender-mcp