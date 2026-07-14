# 将 pytuck/ 包和 examples/renpy_smoke.py 复制到 Ren'Py 工程可导入路径后使用。

init python:
    from pathlib import Path
    from renpy_smoke import run_smoke


label pytuck_smoke:
    $ pytuck_smoke_result = run_smoke(Path(config.savedir) / "pytuck-smoke.pytuck")
    $ pytuck_launch_count = pytuck_smoke_result["launch_count"]
    "Pytuck 已持久化，启动次数：[pytuck_launch_count]"
    return
