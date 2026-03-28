"""
Pytuck JSONL 存储引擎

使用 ZIP 压缩包存储多个 JSONL 文件：一个 `_metadata.json` 加每表一个 `.jsonl` 文件。
"""

import inspect
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, TYPE_CHECKING, Union

from .base import StorageBackend
from .backend_json import JSONBackend
from .versions import get_format_version
from ..common.exceptions import ConfigurationError, EncryptionError, SerializationError
from ..common.options import JsonlBackendOptions
from ..core.types import TypeRegistry

if TYPE_CHECKING:
    from ..core.storage import Table


class JSONLBackend(StorageBackend):
    """JSONL format storage engine (ZIP-based, line-oriented)."""

    ENGINE_NAME = 'jsonl'
    REQUIRED_DEPENDENCIES = []
    FORMAT_VERSION = get_format_version('jsonl')

    def __init__(self, file_path: Union[str, Path], options: JsonlBackendOptions):
        """
        初始化 JSONL 后端

        Args:
            file_path: JSONL ZIP 文件路径
            options: JSONL 后端配置选项
        """
        assert isinstance(options, JsonlBackendOptions), 'options must be an instance of JsonlBackendOptions'
        super().__init__(file_path, options)
        self.options: JsonlBackendOptions = options
        self._setup_json_impl()

    def _setup_json_impl(self) -> None:
        """根据用户指定的 impl 选择 JSON 实现"""
        impl = self.options.impl

        if impl == 'orjson':
            self._setup_orjson()
        elif impl == 'ujson':
            self._setup_ujson()
        elif impl == 'json' or impl is None:
            self._setup_stdlib_json()
        else:
            self._setup_custom_json(impl)

        if not hasattr(self, '_dumps_func') or not hasattr(self, '_loads_func') or not hasattr(self, '_impl_name'):
            raise ConfigurationError(
                f"JSON implementation '{impl}' setup failed: _dumps_func, _loads_func, and _impl_name must be assigned"
            )

    def _setup_orjson(self) -> None:
        """设置 orjson 实现"""
        try:
            import orjson
        except ImportError:
            raise ImportError('orjson not installed. Install with: pip install pytuck[orjson]')

        def dumps_func(obj: Any) -> str:
            result = orjson.dumps(obj)
            return result.decode('utf-8') if isinstance(result, bytes) else result

        self._dumps_func = dumps_func
        self._loads_func = orjson.loads
        self._impl_name = 'orjson'

    def _setup_ujson(self) -> None:
        """设置 ujson 实现"""
        try:
            import ujson  # type: ignore
        except ImportError:
            raise ImportError('ujson not installed. Install with: pip install pytuck[ujson]')

        def dumps_func(obj: Any) -> str:
            try:
                sig = inspect.signature(ujson.dumps)
                kwargs = {}
                if 'ensure_ascii' in sig.parameters:
                    kwargs['ensure_ascii'] = self.options.ensure_ascii
                return ujson.dumps(obj, **kwargs)  # type: ignore[arg-type]
            except Exception:
                return ujson.dumps(obj)

        self._dumps_func = dumps_func
        self._loads_func = ujson.loads
        self._impl_name = 'ujson'

    def _setup_stdlib_json(self) -> None:
        """设置标准库 json 实现"""
        def dumps_func(obj: Any) -> str:
            return json.dumps(obj, ensure_ascii=self.options.ensure_ascii)

        self._dumps_func = dumps_func
        self._loads_func = json.loads
        self._impl_name = 'json'

    def _setup_custom_json(self, impl: str) -> None:
        """自定义 JSON 库处理方法，需要用户覆盖此方法"""
        raise NotImplementedError(
            f"Unsupported JSON library '{impl}'. "
            f"To use a custom JSON library, you must override _setup_custom_json method:\n"
            f"JSONLBackend._setup_custom_json = lambda self, impl: your_custom_logic()\n"
            f"Your custom logic must set self._dumps_func, self._loads_func, and self._impl_name"
        )

    def save(self, tables: Dict[str, 'Table'], *, changed_tables: Optional[Set[str]] = None) -> None:
        """保存所有表数据到 JSONL ZIP 文件"""
        _ = changed_tables
        metadata_bytes = self._dumps_func(self._build_metadata(tables)).encode('utf-8')

        fd, temp_path_str = tempfile.mkstemp(
            dir=str(self.file_path.parent),
            prefix=f'.{self.file_path.stem}.',
            suffix='.tmp'
        )
        os.close(fd)
        temp_path = Path(temp_path_str)

        try:
            if self.options.password:
                from ..common.encrypted_zip import EncryptedZipFile
                with EncryptedZipFile(str(temp_path), self.options.password) as zf:
                    zf.writestr('_metadata.json', metadata_bytes)
                    for table_name, table in tables.items():
                        zf.writestr(f'{table_name}.jsonl', self._generate_jsonl_bytes(table))
            else:
                with zipfile.ZipFile(str(temp_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr('_metadata.json', metadata_bytes)
                    for table_name, table in tables.items():
                        zf.writestr(f'{table_name}.jsonl', self._generate_jsonl_bytes(table))

            temp_path.replace(self.file_path)

        except Exception as e:
            try:
                temp_path.unlink()
            except (FileNotFoundError, OSError):
                pass
            raise SerializationError(f'Failed to save JSONL archive: {e}')

    def load(self) -> Dict[str, 'Table']:
        """从 JSONL ZIP 文件加载所有表数据"""
        if not self.exists():
            raise FileNotFoundError(f'JSONL archive not found: {self.file_path}')

        try:
            with zipfile.ZipFile(str(self.file_path), 'r') as zf:
                encrypted = any((info.flag_bits & 0x1) != 0 for info in zf.infolist())

                if encrypted:
                    if not self.options.password:
                        raise EncryptionError(
                            'JSONL archive is encrypted. Please provide password in JsonlBackendOptions.'
                        )
                    pwd = self.options.password.encode('utf-8')
                else:
                    pwd = None

                metadata = self._load_metadata(zf, pwd)
                tables_schema = metadata.get('tables', {})
                if not isinstance(tables_schema, dict):
                    raise SerializationError('Invalid JSONL tables schema')

                tables = {
                    table_name: self._create_table_from_schema(table_name, schema)
                    for table_name, schema in tables_schema.items()
                }

                for table_name, table in tables.items():
                    jsonl_file = f'{table_name}.jsonl'
                    if jsonl_file in zf.namelist():
                        self._read_jsonl_into_table(zf, jsonl_file, table, pwd)

            self._rebuild_indexes(tables)
            return tables

        except (EncryptionError, SerializationError):
            raise
        except RuntimeError as e:
            if 'Bad password' in str(e) or 'password' in str(e).lower():
                raise EncryptionError('Incorrect password for JSONL archive.')
            raise SerializationError(f'Failed to load JSONL archive: {e}')
        except Exception as e:
            raise SerializationError(f'Failed to load JSONL archive: {e}')

    def exists(self) -> bool:
        """检查文件是否存在"""
        return self.file_path.exists()

    def delete(self) -> None:
        """删除文件"""
        if self.exists():
            self.file_path.unlink()

    def _build_metadata(self, tables: Dict[str, 'Table']) -> Dict[str, Any]:
        """构建 JSONL 元数据"""
        return {
            'engine': self.ENGINE_NAME,
            'format_version': self.FORMAT_VERSION,
            'timestamp': datetime.now().isoformat(),
            'table_count': len(tables),
            'tables': self._build_tables_schema(tables),
        }

    def _build_tables_schema(self, tables: Dict[str, 'Table']) -> Dict[str, Dict[str, Any]]:
        """构建所有表的 schema 字典"""
        tables_schema: Dict[str, Dict[str, Any]] = {}
        for table_name, table in tables.items():
            tables_schema[table_name] = {
                'primary_key': table.primary_key,
                'next_id': table.next_id,
                'comment': table.comment,
                'columns': [
                    {
                        'name': col.name,
                        'type': col.col_type.__name__,
                        'nullable': col.nullable,
                        'primary_key': col.primary_key,
                        'index': col.index,
                        'comment': col.comment,
                        'default': col.default if isinstance(col.default, (int, float, str, bool, type(None))) else None,
                    }
                    for col in table.columns.values()
                ]
            }
        return tables_schema

    def _generate_jsonl_bytes(self, table: 'Table') -> bytes:
        """生成单表 JSONL 字节数据"""
        buffer = io.StringIO()
        for record in table.data.values():
            buffer.write(self._dumps_func(JSONBackend._serialize_record(record)))
            buffer.write('\n')
        return buffer.getvalue().encode('utf-8')

    def _load_metadata(self, zf: zipfile.ZipFile, pwd: Optional[bytes] = None) -> Dict[str, Any]:
        """从 ZIP 中读取元数据"""
        if '_metadata.json' not in zf.namelist():
            raise SerializationError('Missing _metadata.json in JSONL archive')

        with zf.open('_metadata.json', pwd=pwd) as f:
            content = f.read().decode('utf-8')
            metadata = self._loads_func(content)

        if not isinstance(metadata, dict) or metadata.get('engine') != 'jsonl':
            raise SerializationError('Invalid JSONL metadata')
        return metadata

    def _create_table_from_schema(self, table_name: str, schema: Dict[str, Any]) -> 'Table':
        """根据 schema 重建 Table 对象"""
        from ..core.orm import Column
        from ..core.storage import Table

        columns = []
        for col_data in schema.get('columns', []):
            col_type = TypeRegistry.get_type_by_name(col_data['type'])
            column = Column(
                col_type,
                name=col_data['name'],
                nullable=col_data['nullable'],
                primary_key=col_data['primary_key'],
                index=col_data.get('index', False),
                comment=col_data.get('comment'),
                default=col_data.get('default')
            )
            columns.append(column)

        table = Table(
            table_name,
            columns,
            schema.get('primary_key'),
            comment=schema.get('comment')
        )
        table.next_id = schema.get('next_id', 1)
        return table

    def _read_jsonl_into_table(
        self,
        zf: zipfile.ZipFile,
        jsonl_file: str,
        table: 'Table',
        pwd: Optional[bytes] = None
    ) -> None:
        """从 ZIP 中读取单表 JSONL 数据并填充到表中"""
        with zf.open(jsonl_file, pwd=pwd) as f:
            text_stream = io.TextIOWrapper(f, encoding='utf-8')
            for idx, line in enumerate(text_stream):
                if not line.strip():
                    continue

                record_data = self._loads_func(line)
                if not isinstance(record_data, dict):
                    raise SerializationError(f'Invalid JSONL record in {jsonl_file} at line {idx + 1}')

                record = JSONBackend._deserialize_record(record_data, table.columns)

                if table.primary_key:
                    pk = record[table.primary_key]
                else:
                    pk = idx + 1
                    if pk >= table.next_id:
                        table.next_id = pk + 1

                if pk in table.data:
                    raise SerializationError(
                        f"Duplicate primary key '{pk}' in table '{table.name}'"
                    )
                table.data[pk] = record

    def _rebuild_indexes(self, tables: Dict[str, 'Table']) -> None:
        """重建所有表的索引"""
        for table in tables.values():
            for col_name, column in table.columns.items():
                if column.index:
                    if col_name in table.indexes:
                        del table.indexes[col_name]
                    table.build_index(col_name)

    def get_metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        if not self.exists():
            return {}

        file_stat = self.file_path.stat()
        file_size = file_stat.st_size
        modified_time = file_stat.st_mtime

        try:
            with zipfile.ZipFile(str(self.file_path), 'r') as zf:
                encrypted = any((info.flag_bits & 0x1) != 0 for info in zf.infolist())

                if encrypted:
                    if self.options.password:
                        pwd = self.options.password.encode('utf-8')
                        try:
                            metadata = self._load_metadata(zf, pwd)
                        except RuntimeError:
                            return {
                                'engine': self.ENGINE_NAME,
                                'encrypted': True,
                                'file_size': file_size,
                                'modified': modified_time,
                                'json_impl': getattr(self, '_impl_name', 'unknown'),
                                'error': 'incorrect_password'
                            }
                    else:
                        return {
                            'engine': self.ENGINE_NAME,
                            'encrypted': True,
                            'requires_password': True,
                            'file_size': file_size,
                            'modified': modified_time,
                            'json_impl': getattr(self, '_impl_name', 'unknown'),
                        }
                else:
                    metadata = self._load_metadata(zf) if '_metadata.json' in zf.namelist() else {}

            tables = metadata.get('tables', {}) if isinstance(metadata, dict) else {}
            result = {
                'engine': self.ENGINE_NAME,
                'version': metadata.get('format_version', 'unknown') if isinstance(metadata, dict) else 'unknown',
                'file_size': file_size,
                'modified': modified_time,
                'timestamp': metadata.get('timestamp', 'unknown') if isinstance(metadata, dict) else 'unknown',
                'table_count': len(tables) if isinstance(tables, dict) else 0,
                'json_impl': getattr(self, '_impl_name', 'unknown'),
            }
            if encrypted:
                result['encrypted'] = True
            return result
        except Exception:
            return {}

    @classmethod
    def probe(cls, file_path: Union[str, Path]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        轻量探测文件是否为 JSONL 引擎格式

        Returns:
            Tuple[bool, Optional[Dict]]: (是否匹配, 元数据信息或 None)
        """
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return False, {'error': 'file_not_found'}

            file_stat = path.stat()
            if file_stat.st_size == 0:
                return False, {'error': 'empty_file'}

            if not zipfile.is_zipfile(str(path)):
                return False, None

            try:
                with zipfile.ZipFile(str(path), 'r') as zf:
                    namelist = zf.namelist()
                    if '_metadata.json' not in namelist:
                        return False, None

                    encrypted = any((info.flag_bits & 0x1) != 0 for info in zf.infolist())
                    jsonl_files = [name for name in namelist if name.endswith('.jsonl') and not name.startswith('_')]

                    if encrypted:
                        return True, {
                            'engine': 'jsonl',
                            'encrypted': True,
                            'requires_password': True,
                            'jsonl_file_count': len(jsonl_files),
                            'file_size': file_stat.st_size,
                            'modified': file_stat.st_mtime,
                            'confidence': 'medium'
                        }

                    with zf.open('_metadata.json') as f:
                        metadata = json.loads(f.read().decode('utf-8'))

                if not isinstance(metadata, dict):
                    return False, None
                if metadata.get('engine') != 'jsonl' or 'tables' not in metadata:
                    return False, None

                tables = metadata.get('tables', {})
                table_count = len(tables) if isinstance(tables, dict) else 0
                return True, {
                    'engine': 'jsonl',
                    'format_version': metadata.get('format_version'),
                    'table_count': table_count,
                    'jsonl_file_count': len(jsonl_files),
                    'file_size': file_stat.st_size,
                    'modified': file_stat.st_mtime,
                    'timestamp': metadata.get('timestamp'),
                    'confidence': 'high'
                }
            except zipfile.BadZipFile:
                return False, {'error': 'corrupted_zip'}
        except Exception as e:
            return False, {'error': f'probe_exception: {str(e)}'}
