"""PTK7 多表场景下单表修改后的增量 flush benchmark。"""

import argparse
import json
from pathlib import Path
import shutil
from statistics import median
from tempfile import TemporaryDirectory
import time
import tracemalloc
from typing import Any

from pytuck import Column, Storage


def _create_seed(path: Path, table_count: int, records_per_table: int) -> None:
    db = Storage(file_path=path, engine="pytuck")
    for table_index in range(table_count):
        table_name = f"table_{table_index}"
        db.create_table(
            table_name,
            [
                Column(int, name="id", primary_key=True),
                Column(str, name="value", index=True),
                Column(int, name="score"),
            ],
        )
        db.bulk_insert(
            table_name,
            [
                {
                    "id": record_index + 1,
                    "value": f"value-{table_index}-{record_index}",
                    "score": record_index,
                }
                for record_index in range(records_per_table)
            ],
        )
    db.flush()
    db.close()


def run_benchmark(
    records_per_table: int,
    table_count: int,
    repeats: int,
) -> dict[str, Any]:
    """返回多次单表修改后 flush 的中位耗时与峰值内存。"""
    with TemporaryDirectory(prefix="pytuck-incremental-benchmark-") as temp_dir:
        root = Path(temp_dir)
        seed_path = root / "seed.pytuck"
        _create_seed(seed_path, table_count, records_per_table)

        durations: list[float] = []
        peak_memory: list[int] = []
        untouched_materialized: list[int] = []
        for repeat in range(repeats):
            run_path = root / f"run-{repeat}.pytuck"
            shutil.copy2(seed_path, run_path)
            db = Storage(file_path=run_path, engine="pytuck")
            db.update("table_0", 1, {"score": repeat + 100000})

            tracemalloc.start()
            started = time.perf_counter()
            db.flush()
            durations.append(time.perf_counter() - started)
            _current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_memory.append(peak)
            untouched_materialized.append(len(db.tables["table_1"].data))
            db.close()

        return {
            "records_per_table": records_per_table,
            "table_count": table_count,
            "repeats": repeats,
            "flush_median_seconds": median(durations),
            "peak_memory_median_bytes": int(median(peak_memory)),
            "untouched_materialized_rows": max(untouched_materialized),
            "file_size_bytes": seed_path.stat().st_size,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--records", type=int, default=5000)
    parser.add_argument("-t", "--tables", type=int, default=4)
    parser.add_argument("-r", "--repeats", type=int, default=5)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    result = run_benchmark(args.records, args.tables, args.repeats)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output_json is not None:
        args.output_json.expanduser().write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
