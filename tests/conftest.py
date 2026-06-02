import sys
from pathlib import Path

# Add api.py's directory directly so tests can do `from api import ...` without
# executing custom_components/avamet/__init__.py, which imports Home Assistant.
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "avamet"))
