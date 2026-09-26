import sys
from pathlib import Path

tools_dir = str(Path(__file__).resolve().parent.parent / "tools")
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)
