import sys
import os
from pathlib import Path

# Ensure the root directory is in sys.path so 'app' can be imported correctly
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.main import app
