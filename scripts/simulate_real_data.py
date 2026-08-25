#!/usr/bin/env python3
"""Root mirror of simulate_real_data.py."""
import sys
from pathlib import Path

# Add freshroute-optimizer-model to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "freshroute-optimizer-model"))

from scripts.simulate_real_data import main

if __name__ == "__main__":
    main()
