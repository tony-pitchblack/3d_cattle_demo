source .env
hf auth login --token $HF_TOKEN
hf download exponenta/3d_cattle_demo --repo-type dataset --local-dir data/