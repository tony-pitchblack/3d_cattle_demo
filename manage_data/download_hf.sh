SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
source "$SCRIPT_DIR/../.env"
huggingface-cli download \
  exponenta/3d_cattle_demo \
  --local-dir="$SCRIPT_DIR/../data" \
  --token="$HF_TOKEN" \
  --repo-type=dataset