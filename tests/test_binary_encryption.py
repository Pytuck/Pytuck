"""
Pytuck 单文件引擎加密测试

覆盖：
- PTK7 的 none/low/medium/high 写入与读取
- 加密模式不会把记录明文直接写入文件
- probe() 对当前单文件格式的识别
- 错误密码 / 缺少密码时的打开失败
"""

from pathlib import Path
from typing import Optional

import pytest

from pytuck import Column, Storage
from pytuck.backends.backend_binary import BinaryBackend
from pytuck.common.exceptions import EncryptionError
from pytuck.common.options import BinaryBackendOptions


_SECRET_NAME = "Alice-PTK7-Secret"


@pytest.mark.parametrize(
    ("encryption", "password", "file_name", "plaintext_visible"),
    [
        (None, None, "plain_roundtrip.pytuck", True),
        ("low", "secret123", "low_roundtrip.pytuck", False),
        ("medium", "secret123", "medium_roundtrip.pytuck", False),
        ("high", "secret123", "high_roundtrip.pytuck", False),
    ],
)
def test_ptk7_roundtrip_with_supported_encryption_modes(
    tmp_path: Path,
    encryption: Optional[str],
    password: Optional[str],
    file_name: str,
    plaintext_visible: bool,
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
    db.insert("users", {"name": _SECRET_NAME})
    db.flush()
    db.close()

    raw_bytes = db_path.read_bytes()
    if plaintext_visible:
        assert _SECRET_NAME.encode("utf-8") in raw_bytes
    else:
        assert _SECRET_NAME.encode("utf-8") not in raw_bytes

    matched, info = BinaryBackend.probe(db_path)
    assert matched is True
    assert info is not None
    assert info["format_version"] == "PTK7"

    reopen_options = BinaryBackendOptions(password=password) if encryption else BinaryBackendOptions()
    reopened = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=reopen_options,
    )
    assert reopened.select("users", 1)["name"] == _SECRET_NAME
    reopened.close()


@pytest.mark.parametrize("encryption", ["low", "medium", "high"])
def test_ptk7_encrypted_file_requires_password_on_reopen(
    tmp_path: Path,
    encryption: str,
) -> None:
    db_path = tmp_path / f"{encryption}_requires_password.pytuck"
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=BinaryBackendOptions(
            encryption=encryption,
            password="secret123",
        ),
    )
    db.create_table(
        "users",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="name"),
        ],
    )
    db.insert("users", {"name": _SECRET_NAME})
    db.flush()
    db.close()

    with pytest.raises(EncryptionError, match="需要提供密码"):
        Storage(
            file_path=str(db_path),
            engine="pytuck",
            backend_options=BinaryBackendOptions(),
        )


@pytest.mark.parametrize("encryption", ["low", "medium", "high"])
def test_ptk7_encrypted_file_rejects_wrong_password(
    tmp_path: Path,
    encryption: str,
) -> None:
    db_path = tmp_path / f"{encryption}_wrong_password.pytuck"
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=BinaryBackendOptions(
            encryption=encryption,
            password="secret123",
        ),
    )
    db.create_table(
        "users",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="name"),
        ],
    )
    db.insert("users", {"name": _SECRET_NAME})
    db.flush()
    db.close()

    with pytest.raises(EncryptionError, match="密码错误"):
        Storage(
            file_path=str(db_path),
            engine="pytuck",
            backend_options=BinaryBackendOptions(password="wrong-password"),
        )
