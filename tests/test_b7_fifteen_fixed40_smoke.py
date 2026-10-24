"""Run the 15-style smoke in a child process to avoid global monkeypatch leaks."""
import json
from pathlib import Path
import subprocess
import sys


def test_fifteen_fixed40_all_matchups(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "b7_fifteen_fixed40_roundrobin.py"
    p = subprocess.run(
        [sys.executable, str(script), "--start", "0", "--stop", "1",
         "--output", str(tmp_path)],
        cwd=repo, capture_output=True, text=True, timeout=600,
    )
    assert p.returncode == 0, p.stdout[-2000:] + "\n" + p.stderr[-4000:]
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["bouts"] == 240
    assert manifest["incomplete"] == 0
