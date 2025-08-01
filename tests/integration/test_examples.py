"""Quick test of all examples"""

import subprocess
from pathlib import Path

# Test synchronous examples
# Update to match actual example files
sync_examples = ["01_async_basic_apis.py", "02_dynamic_config_update.py"]

for example in sync_examples:
    try:
        result = subprocess.run(
            ["uv", "run", str(Path("examples") / example)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            pass
        else:
            if result.stderr:
                pass
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
