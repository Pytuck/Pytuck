"""
Pytuck 后端模块

提供引擎注册、发现和实例化功能
"""

from .base import StorageBackend

# 零依赖内置后端随包注册；有第三方依赖的扩展后端由 registry 按需加载。
from . import backend_pytuck   # noqa: F401
from . import backend_json     # noqa: F401
from . import backend_jsonl    # noqa: F401
from . import backend_csv      # noqa: F401
from . import backend_sqlite   # noqa: F401

# Re-export registry helpers
from .registry import (
    BackendRegistry,
    get_backend,
    is_valid_pytuck_database,
    get_database_info,
    is_valid_pytuck_database_engine,
    get_available_engines,
    print_available_engines,
)

__all__ = [
    'StorageBackend',
    'BackendRegistry',
    'get_backend',
    'is_valid_pytuck_database',
    'get_database_info',
    'is_valid_pytuck_database_engine',
    'get_available_engines',
    'print_available_engines',
]
