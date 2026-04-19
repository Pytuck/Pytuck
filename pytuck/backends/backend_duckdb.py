"""
Pytuck DuckDB 存储引擎

使用 DuckDB 数据库，支持高性能分析查询和原生 SQL 模式。
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .base import StorageBackend
from .versions import get_format_version
from ..common.exceptions import SerializationError
from ..common.options import DuckdbBackendOptions
from ..connectors.connector_duckdb import DuckDBConnector
from ..core.types import TypeRegistry

if TYPE_CHECKING:
    from ..core.storage import Table

class DuckDBBackend(StorageBackend):
    """DuckDB format storage engine

    使用 DuckDBConnector 进行底层数据库操作。

    支持两种运行模式：
    - 原生 SQL 模式（use_native_sql=True）：只加载 schema，数据直接在数据库中操作
    - 兼容模式（use_native_sql=False）：全量加载到内存
    """

    ENGINE_NAME = 'duckdb'
    REQUIRED_DEPENDENCIES = ['duckdb']
    FORMAT_VERSION = get_format_version('duckdb')

    def __init__(self, file_path: str | Path, options: DuckdbBackendOptions):
        """
        初始化 DuckDB 后端

        Args:
            file_path: DuckDB 数据库文件路径
            options: DuckDB 后端配置选项
        """
        assert isinstance(options, DuckdbBackendOptions), (
            'options must be an instance of DuckdbBackendOptions'
        )
        super().__init__(file_path, options)
        self.options: DuckdbBackendOptions = options
        self._use_native_sql: bool = options.use_native_sql
        self._connector: DuckDBConnector | None = None

    @property
    def use_native_sql(self) -> bool:
        """是否启用原生 SQL 模式"""
        return self._use_native_sql

    def get_connector(self) -> DuckDBConnector:
        """获取或创建连接器（复用连接）"""
        if self._connector is None:
            self._connector = DuckDBConnector(str(self.file_path), self.options)
            self._connector.connect()
        return self._connector

    def close(self) -> None:
        """关闭连接器"""
        if self._connector is not None:
            try:
                self._connector.checkpoint()
            except Exception:
                pass
            self._connector.close()
            self._connector = None

    def supports_lazy_loading(self) -> bool:
        """原生 SQL 模式下只加载 schema"""
        return self._use_native_sql

    def populate_tables_with_data(self, tables: dict[str, 'Table']) -> None:
        """从 DuckDB 填充表数据（用于原生 SQL 模式下的迁移场景）"""
        if not self._use_native_sql:
            return

        connector = self.get_connector()

        for table_name, table in tables.items():
            if table.data:
                continue
            self._populate_table_data(connector, table_name, table)

    def save(self, tables: dict[str, 'Table'], *, changed_tables: set[str] | None = None) -> None:
        """保存数据到 DuckDB 数据库"""
        if self._use_native_sql:
            self._save_schema_only(tables)
        else:
            self._save_full(tables)

    def save_full(self, tables: dict[str, 'Table']) -> None:
        """全量保存所有表数据（用于迁移场景）"""
        self._save_full(tables)

    def _save_full(self, tables: dict[str, 'Table']) -> None:
        """全量保存所有表数据到 DuckDB 数据库（兼容模式）"""
        try:
            connector = DuckDBConnector(str(self.file_path), self.options)
            with connector:
                self._ensure_metadata_tables(connector)
                self._upsert_metadata_value(connector, 'format_version', str(self.FORMAT_VERSION))
                self._upsert_metadata_value(connector, 'timestamp', datetime.now().isoformat())

                for table_name, table in tables.items():
                    self._save_table(connector, table_name, table)

                connector.commit()
        except Exception as e:
            raise SerializationError(f'Failed to save to DuckDB: {e}')

    def _save_schema_only(self, tables: dict[str, 'Table']) -> None:
        """只保存 schema 元数据（原生 SQL 模式）"""
        try:
            connector = self.get_connector()
            self._ensure_metadata_tables(connector)
            self._upsert_metadata_value(connector, 'format_version', str(self.FORMAT_VERSION))
            self._upsert_metadata_value(connector, 'timestamp', datetime.now().isoformat())

            for table_name, table in tables.items():
                table_exists = connector.table_exists(table_name)
                if not table_exists:
                    connector.create_table(table_name, self._build_columns_def(table), table.primary_key)
                    self._create_indexes(connector, table_name, table)
                self._apply_comments(connector, table_name, table)

            connector.commit()
            connector.checkpoint()
        except Exception as e:
            raise SerializationError(f'Failed to save schema to DuckDB: {e}')

    def load(self) -> dict[str, 'Table']:
        """加载数据"""
        if not self.exists():
            raise FileNotFoundError(f'DuckDB database not found: {self.file_path}')

        if self._use_native_sql:
            return self._load_schema_only()
        return self._load_full()

    def _load_full(self) -> dict[str, 'Table']:
        """全量加载所有表数据（兼容模式）"""
        try:
            connector = DuckDBConnector(str(self.file_path), self.options)
            with connector:
                tables: dict[str, 'Table'] = {}
                for table_name in connector.get_table_names(exclude_system=True):
                    table = self._load_table_from_database(connector, table_name)
                    tables[table_name] = table
                return tables
        except Exception as e:
            raise SerializationError(f'Failed to load from DuckDB: {e}')

    def _load_schema_only(self) -> dict[str, 'Table']:
        """只加载 schema 元数据（原生 SQL 模式）"""
        try:
            connector = self.get_connector()
            tables: dict[str, 'Table'] = {}
            for table_name in connector.get_table_names(exclude_system=True):
                table = self._load_table_schema_from_database(connector, table_name)
                tables[table_name] = table
            return tables
        except Exception as e:
            raise SerializationError(f'Failed to load schema from DuckDB: {e}')

    def _load_table_schema_from_database(
        self,
        connector: DuckDBConnector,
        table_name: str
    ) -> 'Table':
        """从 DuckDB 实际表和 catalog 加载单表 schema"""
        from ..core.orm import Column
        from ..core.storage import Table

        columns_info, primary_key = connector.get_table_schema(table_name)
        table_comment = connector.get_table_comment(table_name)

        columns: list['Column'] = []
        for col_info in columns_info:
            column = Column(
                col_info['type'],
                name=col_info['name'],
                nullable=col_info.get('nullable', True),
                primary_key=col_info.get('primary_key', False),
                index=col_info.get('index', False),
                comment=col_info.get('comment'),
            )
            columns.append(column)

        table = Table(table_name, columns, primary_key, comment=table_comment)

        if (
            table.primary_key
            and table.primary_key in table.columns
            and table.columns[table.primary_key].col_type == int
        ):
            table.next_id = connector.get_next_id(table_name, table.primary_key)
        else:
            table.next_id = 1

        return table

    def _load_table_from_database(
        self,
        connector: DuckDBConnector,
        table_name: str
    ) -> 'Table':
        """从 DuckDB 实际表、catalog 与数据加载单个表"""
        table = self._load_table_schema_from_database(connector, table_name)
        self._populate_table_data(connector, table_name, table)

        for col_name, column in table.columns.items():
            if column.index:
                if col_name in table.indexes:
                    del table.indexes[col_name]
                table.build_index(col_name)

        return table

    def exists(self) -> bool:
        """检查数据库文件是否存在"""
        return self.file_path.exists()

    def delete(self) -> None:
        """删除数据库文件"""
        if self.exists():
            self.file_path.unlink()

    @staticmethod
    def _ensure_metadata_tables(connector: DuckDBConnector) -> None:
        """确保元数据表存在"""
        connector.execute(
            'CREATE TABLE IF NOT EXISTS _pytuck_metadata ('
            'key VARCHAR PRIMARY KEY, '
            'value VARCHAR'
            ')'
        )

    @staticmethod
    def _upsert_metadata_value(connector: DuckDBConnector, key: str, value: str) -> None:
        """更新或插入元数据键值"""
        connector.execute('DELETE FROM _pytuck_metadata WHERE key = ?', (key,))
        connector.execute('INSERT INTO _pytuck_metadata (key, value) VALUES (?, ?)', (key, value))

    @staticmethod
    def _build_columns_def(table: 'Table') -> list[dict[str, Any]]:
        """构建连接器 create_table 所需的列定义"""
        return [
            {
                'name': col.name,
                'type': col.col_type,
                'nullable': col.nullable,
                'primary_key': col.primary_key
            }
            for col in table.columns.values()
        ]

    def _save_table(
        self,
        connector: DuckDBConnector,
        table_name: str,
        table: 'Table'
    ) -> None:
        """保存单个表"""
        if connector.table_exists(table_name):
            connector.drop_table(table_name)

        connector.create_table(table_name, self._build_columns_def(table), table.primary_key)
        self._create_indexes(connector, table_name, table)
        self._apply_comments(connector, table_name, table)

        if len(table.data) > 0:
            columns = list(table.columns.keys())
            serialized_records = [
                self._serialize_record_for_duckdb(record, table.columns)
                for record in table.data.values()
            ]
            connector.insert_records(table_name, columns, serialized_records)

    @classmethod
    def _create_indexes(
        cls,
        connector: DuckDBConnector,
        table_name: str,
        table: 'Table'
    ) -> None:
        """创建非主键索引"""
        for col_name, col in table.columns.items():
            if col.index and not col.primary_key:
                index_name = f'idx_{table_name}_{col_name}'
                connector.execute(
                    f'CREATE INDEX {cls._quote_identifier(index_name)} '
                    f'ON {cls._quote_identifier(table_name)}'
                    f'({cls._quote_identifier(col_name)})'
                )

    @staticmethod
    def _apply_comments(
        connector: DuckDBConnector,
        table_name: str,
        table: 'Table'
    ) -> None:
        """把表备注和列备注写入 DuckDB 原生 catalog"""
        connector.set_table_comment(table_name, table.comment)
        for col_name, col in table.columns.items():
            connector.set_column_comment(table_name, col_name, col.comment)

    @staticmethod
    def _serialize_record_for_duckdb(
        record: dict[str, Any],
        columns: dict[str, Any]
    ) -> dict[str, Any]:
        """序列化记录以适应 DuckDB 存储"""
        result: dict[str, Any] = {}
        for key, value in record.items():
            if value is None:
                result[key] = None
            elif key in columns:
                col_type = columns[key].col_type
                if col_type in (list, dict):
                    result[key] = json.dumps(value, ensure_ascii=False)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    @staticmethod
    def _deserialize_record(
        record: dict[str, Any],
        columns: dict[str, Any]
    ) -> dict[str, Any]:
        """反序列化单条记录"""
        result: dict[str, Any] = {}
        for col_name, value in record.items():
            if col_name not in columns or value is None:
                result[col_name] = value
                continue

            column = columns[col_name]
            if column.col_type == bool and isinstance(value, int):
                value = bool(value)
            elif column.col_type in (datetime, date, timedelta) and isinstance(value, str):
                value = TypeRegistry.deserialize_from_text(value, column.col_type)
            elif column.col_type in (list, dict) and isinstance(value, str):
                value = json.loads(value)

            result[col_name] = value

        return result

    @classmethod
    def _deserialize_row(
        cls,
        row: tuple,
        col_names: list[str],
        columns: dict[str, Any]
    ) -> dict[str, Any]:
        """反序列化单行数据"""
        raw_record = dict(zip(col_names, row))
        return cls._deserialize_record(raw_record, columns)

    @classmethod
    def _populate_table_data(
        cls,
        connector: DuckDBConnector,
        table_name: str,
        table: 'Table'
    ) -> None:
        """把数据库中的数据填充到 Table.data"""
        if table.primary_key is None:
            cursor = connector.execute(
                f'SELECT rowid, * FROM {cls._quote_identifier(table_name)}'
            )
        else:
            cursor = connector.execute(
                f'SELECT * FROM {cls._quote_identifier(table_name)}'
            )
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        for row in rows:
            record = cls._deserialize_row(row, col_names, table.columns)
            if table.primary_key:
                pk = record.get(table.primary_key)
                if pk is None:
                    pk = table.next_id
                    table.next_id += 1
            else:
                pk = record.pop('rowid', None)
                if pk is None:
                    pk = table.next_id
                    table.next_id += 1
            table.data[pk] = record

    def get_metadata(self) -> dict[str, Any]:
        """获取元数据"""
        if not self.exists():
            return {}

        try:
            file_stat = self.file_path.stat()
            metadata: dict[str, Any] = {
                'engine': 'duckdb',
                'file_size': file_stat.st_size,
                'modified': file_stat.st_mtime
            }

            connector = DuckDBConnector(str(self.file_path), self.options)
            with connector:
                try:
                    if connector.table_exists('_pytuck_metadata'):
                        cursor = connector.execute(
                            'SELECT value FROM _pytuck_metadata WHERE key = ?',
                            ('format_version',)
                        )
                        row = cursor.fetchone()
                        if row:
                            metadata['format_version'] = row[0]

                        cursor = connector.execute(
                            'SELECT value FROM _pytuck_metadata WHERE key = ?',
                            ('timestamp',)
                        )
                        row = cursor.fetchone()
                        if row:
                            metadata['timestamp'] = row[0]
                except Exception:
                    pass

                metadata['table_count'] = len(connector.get_table_names(exclude_system=True))

            return metadata
        except Exception:
            return {}

    def supports_server_side_pagination(self) -> bool:
        """DuckDB 支持服务端分页"""
        return True

    def query_with_pagination(
        self,
        table_name: str,
        conditions: list[dict[str, Any]],
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_desc: bool = False
    ) -> dict[str, Any]:
        """使用 SQL LIMIT/OFFSET 实现后端分页"""
        if not self.exists():
            return {'records': [], 'total_count': 0, 'has_more': False}

        try:
            connector = DuckDBConnector(str(self.file_path), self.options)
            with connector:
                if not connector.table_exists(table_name):
                    return {'records': [], 'total_count': 0, 'has_more': False}

                where_clause = ''
                params: list[Any] = []
                if conditions:
                    where_parts: list[str] = []
                    for condition in conditions:
                        field = condition['field']
                        operator = condition.get('operator', '=')
                        value = condition['value']

                        if operator == 'LIKE':
                            where_parts.append(f'"{field}" LIKE ?')
                            params.append(f'%{value}%')
                        elif operator == 'STARTSWITH':
                            where_parts.append(f'"{field}" LIKE ?')
                            params.append(f'{value}%')
                        elif operator == 'ENDSWITH':
                            where_parts.append(f'"{field}" LIKE ?')
                            params.append(f'%{value}')
                        elif operator == 'IN':
                            if isinstance(value, (list, tuple)) and len(value) > 0:
                                placeholders = ', '.join('?' for _ in value)
                                where_parts.append(f'"{field}" IN ({placeholders})')
                                params.extend(value)
                        elif operator in ('=', '!=', '>', '<', '>=', '<='):
                            where_parts.append(f'"{field}" {operator} ?')
                            params.append(value)

                    if where_parts:
                        where_clause = 'WHERE ' + ' AND '.join(where_parts)

                order_clause = ''
                if order_by:
                    direction = 'DESC' if order_desc else 'ASC'
                    order_clause = f'ORDER BY "{order_by}" {direction}'

                limit_clause = ''
                if limit is not None:
                    limit_clause = f'LIMIT {limit}'
                    if offset > 0:
                        limit_clause += f' OFFSET {offset}'

                count_sql = f'SELECT COUNT(*) FROM "{table_name}" {where_clause}'
                cursor = connector.execute(count_sql, tuple(params))
                total_count = cursor.fetchone()[0] if cursor else 0

                data_sql = f'SELECT * FROM "{table_name}" {where_clause} {order_clause} {limit_clause}'
                cursor = connector.execute(data_sql, tuple(params))
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                records = []
                for row in rows:
                    record: dict[str, Any] = {}
                    for col_name, value in zip(col_names, row):
                        record[col_name] = value
                    records.append(record)

                has_more = False
                if limit is not None:
                    has_more = (offset + len(records)) < total_count

                return {
                    'records': records,
                    'total_count': total_count,
                    'has_more': has_more
                }
        except Exception as e:
            raise NotImplementedError(f'DuckDB pagination failed: {e}')

    @classmethod
    def probe(cls, file_path: str | Path) -> tuple[bool, dict[str, Any] | None]:
        """轻量探测文件是否为 DuckDB 引擎格式"""
        try:
            file_path = Path(file_path).expanduser()
            if not file_path.exists():
                return False, {'error': 'file_not_found'}

            file_stat = file_path.stat()
            file_size = file_stat.st_size
            if file_size == 0:
                return False, {'error': 'empty_file'}

            try:
                import duckdb
            except (ImportError, ModuleNotFoundError):
                return False, {'error': 'duckdb_not_installed'}

            try:
                conn = duckdb.connect(str(file_path), read_only=True)
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_type = 'BASE TABLE' "
                        "AND table_schema NOT IN ('information_schema', 'pg_catalog') "
                        "AND table_name NOT LIKE '_pytuck_%'"
                    )
                    table_count_row = cursor.fetchone()
                    table_count = table_count_row[0] if table_count_row is not None else 0

                    format_version = None
                    timestamp = None
                    cursor = conn.execute(
                        "SELECT table_schema FROM information_schema.tables "
                        "WHERE table_name = '_pytuck_metadata' "
                        "ORDER BY CASE WHEN table_schema = 'main' THEN 0 ELSE 1 END "
                        "LIMIT 1"
                    )
                    metadata_row = cursor.fetchone()
                    if metadata_row:
                        metadata_schema = metadata_row[0]
                        metadata_table = (
                            f'{cls._quote_identifier(metadata_schema)}.'
                            f'{cls._quote_identifier("_pytuck_metadata")}'
                        )
                        try:
                            cursor = conn.execute(
                                f"SELECT value FROM {metadata_table} WHERE key = 'format_version'"
                            )
                            version_result = cursor.fetchone()
                            if version_result:
                                format_version = version_result[0]

                            cursor = conn.execute(
                                f"SELECT value FROM {metadata_table} WHERE key = 'timestamp'"
                            )
                            timestamp_result = cursor.fetchone()
                            if timestamp_result:
                                timestamp = timestamp_result[0]
                        except Exception:
                            pass

                    return True, {
                        'engine': 'duckdb',
                        'format_version': format_version,
                        'table_count': table_count,
                        'file_size': file_size,
                        'modified': file_stat.st_mtime,
                        'timestamp': timestamp,
                        'confidence': 'high'
                    }
                finally:
                    conn.close()
            except Exception as e:
                return False, {'error': f'duckdb_error: {str(e)}'}
        except Exception as e:
            return False, {'error': f'probe_exception: {str(e)}'}

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """使用标准 SQL 双引号安全引用标识符"""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'
