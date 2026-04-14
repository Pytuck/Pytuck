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
        ("medium", "secret123", "medium_ptk7.pytuck"),
        ("high", "secret123", "high_ptk7.pytuck"),
    ],
)
def test_ptk7_accepts_none_low_medium_and_high(
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

    reopen_options = BinaryBackendOptions(password=password) if encryption else BinaryBackendOptions()
    reopened = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=reopen_options,
    )
    assert reopened.select("users", 1)["name"] == "Alice"
    reopened.close()


@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_ptk7_rejects_configured_encryption_without_password(
    tmp_path: Path,
    level: str,
) -> None:
    with pytest.raises(ConfigurationError, match="加密需要提供密码"):
        Storage(
            file_path=str(tmp_path / f"enc_{level}_ptk7.pytuck"),
            engine="pytuck",
            backend_options=BinaryBackendOptions(
                encryption=level,
            ),
        )


@pytest.mark.parametrize("level", ["ultra", "legacy"])
def test_ptk7_rejects_invalid_encryption_level(
    tmp_path: Path,
    level: str,
) -> None:
    with pytest.raises(ConfigurationError, match="无效的加密等级"):
        Storage(
            file_path=str(tmp_path / f"enc_{level}_ptk7.pytuck"),
            engine="pytuck",
            backend_options=BinaryBackendOptions(
                encryption=level,
                password="secret123",
            ),
        )
