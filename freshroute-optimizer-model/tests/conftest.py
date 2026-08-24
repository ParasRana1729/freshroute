import sys
from pathlib import Path

# Ensure `freshroute-optimizer-model` root is on sys.path for `from core.*` imports
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
# Also repo root for docs path resolution
if str(root.parent) not in sys.path:
    sys.path.insert(0, str(root.parent))
