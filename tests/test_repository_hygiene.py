import re
import shutil
import subprocess
import pytest

PATTERN = re.compile(r"(__pycache__/|\.pyc$|\.pyo$|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.sqlite$|\.db$|^outputs/|^data/knowledge_space/)")


def test_no_tracked_generated_artifacts():
    if shutil.which("git") is None:
        pytest.skip("git is unavailable")

    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        pytest.skip("git ls-files failed in this environment")

    offenders = [p for p in proc.stdout.splitlines() if PATTERN.search(p)]
    assert not offenders, f"Tracked generated/cache artifacts found: {offenders}"
