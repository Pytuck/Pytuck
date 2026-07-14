"""
Pytuck 单文件引擎加密测试

覆盖：
- Pytuck 单文件格式的 none/low/medium/high 写入与读取
- 加密模式不会把记录明文直接写入文件
- probe() 对当前单文件格式的识别
- 错误密码 / 缺少密码时的打开失败
"""

from dataclasses import replace
from pathlib import Path
from typing import Optional

import pytest

from pytuck import Column, Storage
from pytuck.backends.backend_pytuck import PytuckBackend
from pytuck.backends.pytuck_format import (
    AUTH_TAG_SIZE,
    CRYPTO_META_STRUCT,
    FileHeaderV7,
    HEADER_STRUCT,
)
from pytuck.common.crypto import CryptoProvider, get_cipher
from pytuck.common.exceptions import EncryptionError
from pytuck.common.options import PytuckBackendOptions


_SECRET_NAME = "Alice-Pytuck-Secret"


@pytest.mark.parametrize(
    ("encryption", "password", "file_name", "plaintext_visible"),
    [
        (None, None, "plain_roundtrip.pytuck", True),
        ("low", "secret123", "low_roundtrip.pytuck", False),
        ("medium", "secret123", "medium_roundtrip.pytuck", False),
        ("high", "secret123", "high_roundtrip.pytuck", False),
    ],
)
def test_pytuck_roundtrip_with_supported_encryption_modes(
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
        backend_options=PytuckBackendOptions(
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

    matched, info = PytuckBackend.probe(db_path)
    assert matched is True
    assert info is not None
    assert info["format_version"] == "PTK7"

    reopen_options = PytuckBackendOptions(password=password) if encryption else PytuckBackendOptions()
    reopened = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=reopen_options,
    )
    assert reopened.select("users", 1)["name"] == _SECRET_NAME
    reopened.close()


@pytest.mark.parametrize("encryption", ["low", "medium", "high"])
def test_pytuck_encrypted_file_requires_password_on_reopen(
    tmp_path: Path,
    encryption: str,
) -> None:
    db_path = tmp_path / f"{encryption}_requires_password.pytuck"
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=PytuckBackendOptions(
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
            backend_options=PytuckBackendOptions(),
        )


@pytest.mark.parametrize("encryption", ["low", "medium", "high"])
def test_pytuck_encrypted_file_rejects_wrong_password(
    tmp_path: Path,
    encryption: str,
) -> None:
    db_path = tmp_path / f"{encryption}_wrong_password.pytuck"
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=PytuckBackendOptions(
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
            backend_options=PytuckBackendOptions(password="wrong-password"),
        )


def test_pytuck_authenticated_file_rejects_tampering(tmp_path: Path) -> None:
    """新写入的 high 文件任一密文字节被修改后都必须拒绝打开。"""
    db_path = tmp_path / 'authenticated_tamper.pytuck'
    options = PytuckBackendOptions(encryption='high', password='secret123')
    db = Storage(file_path=db_path, engine='pytuck', backend_options=options)
    db.create_table(
        'users',
        [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
        ],
    )
    db.insert('users', {'name': _SECRET_NAME})
    db.flush()
    db.close()

    raw = bytearray(db_path.read_bytes())
    header = FileHeaderV7.unpack(raw[:HEADER_STRUCT.size])
    assert header.is_authenticated() is True
    raw[-AUTH_TAG_SIZE - 1] ^= 0x01
    db_path.write_bytes(raw)

    with pytest.raises(EncryptionError, match='完整性校验失败'):
        Storage(file_path=db_path, engine='pytuck', backend_options=options)


def test_pytuck_reads_legacy_unauthenticated_ptk7(tmp_path: Path) -> None:
    """认证标签引入前的 PTK7 加密布局仍应可读取。"""
    db_path = tmp_path / 'legacy_encrypted.pytuck'
    password = 'secret123'
    options = PytuckBackendOptions(encryption='high', password=password)
    db = Storage(file_path=db_path, engine='pytuck', backend_options=options)
    db.create_table(
        'users',
        [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
        ],
    )
    db.insert('users', {'name': _SECRET_NAME})
    db.flush()
    db.close()

    raw = db_path.read_bytes()
    header = FileHeaderV7.unpack(raw[:HEADER_STRUCT.size])
    metadata_start = HEADER_STRUCT.size
    metadata_end = metadata_start + CRYPTO_META_STRUCT.size
    metadata = raw[metadata_start:metadata_end]
    salt = metadata[:16]
    master_key = CryptoProvider.derive_key(password, salt, 'high')
    payload_start = header.table_ref_offset + header.table_ref_size
    payload_end = len(raw) - AUTH_TAG_SIZE
    plaintext = get_cipher(
        'high',
        CryptoProvider.derive_encryption_key(master_key),
    ).decrypt(raw[payload_start:payload_end])
    legacy_payload = get_cipher('high', master_key).encrypt(plaintext)

    legacy_header = replace(
        header,
        flags=header.flags & ~FileHeaderV7.FLAG_AUTHENTICATED,
        file_size=header.file_size - AUTH_TAG_SIZE,
    )
    db_path.write_bytes(
        legacy_header.pack()
        + raw[HEADER_STRUCT.size:payload_start]
        + legacy_payload
    )

    reopened = Storage(file_path=db_path, engine='pytuck', backend_options=options)
    assert reopened.select('users', 1)['name'] == _SECRET_NAME
    reopened.close()
