from pathlib import Path
from typing import Optional

import pytest

from pytuck import Column, Storage
from pytuck.common.exceptions import ConfigurationError
from pytuck.common.options import BinaryBackendOptions


@pytest.mark.parametrize(
    ("encryption", "password", "file_name"),
    [
        (None, None, "plain_ptk7.pytuck"),
        ("low", "secret123", "low_ptk7.pytuck"),
    ],
)
def test_ptk7_accepts_none_and_low_only(
    tmp_path: Path,
    encryption: Optional[str],
    password: Optional[str],
    file_name: str,
) -> None:
    db_path = tmp_path / file_name
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=BinaryBackendOptions(
            encryption=encryption,
            password=password,
        ),
    )
    db.create_table(
        "users",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="name"),
        ],
    )
    db.insert("users", {"name": "Alice"})
    db.flush()
    db.close()

    reopened = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=BinaryBackendOptions(
            encryption=encryption,
            password=password,
        ),
    )
    assert reopened.select("users", 1)["name"] == "Alice"
    reopened.close()


@pytest.mark.parametrize("level", ["medium", "high"])
def test_ptk7_rejects_new_medium_or_high_encryption(
    tmp_path: Path,
    level: str,
) -> None:
    with pytest.raises(ConfigurationError, match="当前 Pytuck 单文件引擎仅支持.*low"):
        Storage(
            file_path=str(tmp_path / f"enc_{level}_ptk7.pytuck"),
            engine="pytuck",
            backend_options=BinaryBackendOptions(
                encryption=level,
                password="secret123",
            ),
        )

