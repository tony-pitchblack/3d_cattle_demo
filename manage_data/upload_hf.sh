SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
source "$SCRIPT_DIR/../.env"
huggingface-cli upload \
  exponenta/3d_cattle_demo \
  "$SCRIPT_DIR/../data" \
  . \
  --repo-type=dataset \
  --token="$HF_TOKEN"