#!/usr/bin/env python3
"""
JSON / orjson 专项 benchmark。

仅对 JSON 与 JSONL 两种引擎进行对比，观察标准库 json 与 orjson
在持久化相关路径上的差异。

用法:
    python tests/benchmark/benchmark_json_impl.py
    python tests/benchmark/benchmark_json_impl.py -n 100000
    python tests/benchmark/benchmark_json_impl.py --output-json /tmp/pytuck-json-impl.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pytuck import Column, PureBaseModel, Storage, declarative_base
from pytuck.common.options import JsonBackendOptions, JsonlBackendOptions


DEFAULT_RECORD_COUNT = 100000
CASES: list[tuple[str, str]] = [
    ("json", "json"),
    ("json", "orjson"),
    ("jsonl", "json"),
    ("jsonl", "orjson"),
]

EXTENSIONS = {
    "json": ".json",
    "jsonl": ".zip",
}


class Timer:
    """简单计时器。"""

    def __init__(self) -> None:
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self._start


def format_time(seconds: float) -> str:
    """格式化时间。"""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.1f}μs"
    if seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    return f"{seconds:.2f}s"


def format_size(bytes_size: int) -> str:
    """格式化文件大小。"""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    if bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f}KB"
    return f"{bytes_size / (1024 * 1024):.2f}MB"


def make_records(count: int) -> list[dict[str, Any]]:
    """生成 benchmark 数据。"""
    return [
        {
            "name": f"User_{i}",
            "email": f"user{i}@example.com",
            "age": 20 + (i % 50),
            "score": float(i % 100) / 10.0,
            "active": i % 2 == 0,
            "bio": f"用户 {i} 的资料信息，用于观察 JSON / orjson 在文本字段上的序列化路径。",
        }
        for i in range(1, count + 1)
    ]


def build_options(engine: str, impl: str) -> JsonBackendOptions | JsonlBackendOptions:
    """构造后端选项。"""
    if engine == "json":
        return JsonBackendOptions(indent=None, ensure_ascii=False, impl=impl)
    return JsonlBackendOptions(ensure_ascii=False, impl=impl)


def get_file_size(path: Path) -> int:
    """获取文件大小。"""
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total
    return 0


def is_impl_available(impl: str) -> bool:
    """检查 JSON 实现是否可用。"""
    if impl == "json":
        return True
    if impl == "orjson":
        try:
            import orjson  # noqa: F401
        except ImportError:
            return False
        return True
    return False


class JsonImplBenchmark:
    """单个引擎 + JSON 实现组合的 benchmark。"""

    def __init__(self, engine: str, impl: str, temp_dir: Path) -> None:
        self.engine = engine
        self.impl = impl
        self.temp_dir = temp_dir
        self.file_path = temp_dir / f"benchmark_{engine}_{impl}{EXTENSIONS[engine]}"
        self.options = build_options(engine, impl)

    def setup_database(self, records: list[dict[str, Any]]) -> Storage:
        """创建数据库并填充记录。"""
        if self.file_path.exists():
            if self.file_path.is_dir():
                shutil.rmtree(self.file_path)
            else:
                self.file_path.unlink()

        db = Storage(file_path=self.file_path, engine=self.engine, backend_options=self.options)
        Base = declarative_base(db)

        class BenchmarkUser(Base):
            __tablename__ = "benchmark_users"

            id = Column(int, primary_key=True)
            name = Column(str, nullable=False, index=True)
            email = Column(str, nullable=True)
            age = Column(int, nullable=True)
            score = Column(float, nullable=True)
            active = Column(bool, nullable=True)
            bio = Column(str, nullable=True)

        db.bulk_insert(BenchmarkUser.__tablename__, records)
        return db

    def benchmark_save(self, db: Storage) -> float:
        """测试 flush 写盘。"""
        with Timer() as timer:
            db.flush()
        return timer.elapsed

    def benchmark_load(self) -> float:
        """测试加载。"""
        with Timer() as timer:
            db = Storage(file_path=self.file_path, engine=self.engine, backend_options=self.options)
        db.close()
        return timer.elapsed

    def benchmark_reopen(self) -> float:
        """测试重新打开。"""
        with Timer() as timer:
            db = Storage(file_path=self.file_path, engine=self.engine, backend_options=self.options)
        db.close()
        return timer.elapsed

    def benchmark_reopen_first_query(self, count: int) -> float:
        """测试重开后的首次主键查询。"""
        sample_id = min(count, max(1, (count + 1) // 2))
        db = Storage(file_path=self.file_path, engine=self.engine, backend_options=self.options)
        try:
            with Timer() as timer:
                row = db.select("benchmark_users", sample_id)
                _ = row.get("name")
            return timer.elapsed
        finally:
            db.close()

    def run(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """执行单个组合的 benchmark。"""
        db = self.setup_database(records)
        try:
            save_time = self.benchmark_save(db)
            file_size = get_file_size(self.file_path)
        finally:
            db.close()

        return {
            "engine": self.engine,
            "impl": self.impl,
            "record_count": len(records),
            "save": save_time,
            "load": self.benchmark_load(),
            "reopen": self.benchmark_reopen(),
            "reopen_first_query": self.benchmark_reopen_first_query(len(records)),
            "file_size": file_size,
        }


def render_markdown_table(results: list[dict[str, Any]]) -> str:
    """渲染 Markdown 表格。"""
    lines = [
        "| 引擎 | 实现 | 保存 | 加载 | 重开 | 重开后首次查询 | 文件大小 |",
        "|------|------|------|------|------|----------------|----------|",
    ]
    for item in results:
        lines.append(
            "| "
            f"{item['engine'].upper()} | "
            f"{item['impl']} | "
            f"{format_time(item['save'])} | "
            f"{format_time(item['load'])} | "
            f"{format_time(item['reopen'])} | "
            f"{format_time(item['reopen_first_query'])} | "
            f"{format_size(item['file_size'])} |"
        )
    return "\n".join(lines)


def render_speedup_summary(results: list[dict[str, Any]]) -> str:
    """渲染同引擎 json vs orjson 的相对速度摘要。"""
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(item["engine"], {})[item["impl"]] = item

    lines: list[str] = []
    for engine in ("json", "jsonl"):
        group = grouped.get(engine, {})
        stdlib = group.get("json")
        accelerated = group.get("orjson")
        if not stdlib or not accelerated:
            continue
        lines.append(
            f"- `{engine}`: `orjson` 相比标准库 `json`，"
            f"`save` 约快 `{stdlib['save'] / accelerated['save']:.2f}x`，"
            f"`load` 约快 `{stdlib['load'] / accelerated['load']:.2f}x`，"
            f"`reopen` 约快 `{stdlib['reopen'] / accelerated['reopen']:.2f}x`。"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="JSON / orjson 专项 benchmark")
    parser.add_argument("-n", "--records", type=int, default=DEFAULT_RECORD_COUNT, help="记录数（默认 100000）")
    parser.add_argument("--output-json", type=Path, default=None, help="将原始结果输出为 JSON 文件")
    args = parser.parse_args()

    records = make_records(args.records)
    temp_dir = Path(tempfile.mkdtemp(prefix="pytuck_json_impl_", dir=tempfile.gettempdir()))

    try:
        results: list[dict[str, Any]] = []
        for engine, impl in CASES:
            if not is_impl_available(impl):
                print(f"跳过 {engine}/{impl}：实现不可用")
                continue
            bench = JsonImplBenchmark(engine, impl, temp_dir)
            result = bench.run(records)
            results.append(result)
            print(
                f"{engine}/{impl}: "
                f"save={format_time(result['save'])}, "
                f"load={format_time(result['load'])}, "
                f"reopen={format_time(result['reopen'])}, "
                f"first_query={format_time(result['reopen_first_query'])}, "
                f"size={format_size(result['file_size'])}"
            )

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "record_count": args.records,
            "results": results,
        }

        if args.output_json is not None:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        print("\n## Markdown Table\n")
        print(render_markdown_table(results))
        print("\n## Speedup Summary\n")
        print(render_speedup_summary(results))
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
