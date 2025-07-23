source ./.env
huggingface-cli upload exponenta/3d_cattle_demo data/ . --repo-type=dataset --token=$HF_TOKEN