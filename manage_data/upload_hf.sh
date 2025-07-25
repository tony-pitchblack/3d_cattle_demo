SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
source "$SCRIPT_DIR/../.env"
git -C "$SCRIPT_DIR/../data" push \
  git@hf.co:datasets/exponenta/3d_cattle_demo \
  HEAD
