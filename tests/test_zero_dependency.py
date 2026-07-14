"""零依赖核心边界的回归测试。"""

from pathlib import Path
import subprocess
import sys


def test_zero_dependency_smoke_runs_in_fresh_process() -> None:
    """独立进程导入核心时不得加载任何可选依赖。"""
    script = Path(__file__).with_name("zero_dependency_smoke.py")
    completed = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Pytuck 零依赖 wheel smoke 通过" in completed.stdout
