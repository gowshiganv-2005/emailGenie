import sys
from pathlib import Path

# Ensure project root is in path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.main import app
