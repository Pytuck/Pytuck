"""
DuckDB 数据库连接器

提供 DuckDB 数据库的统一操作接口
"""

import ast
import json
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Tuple, Optional, Type, Set

from .base import DatabaseConnector
from ..common.options import DuckdbConnectorOptions
from ..common.exceptions import DatabaseConnectionError, TableNotFoundError
from ..common.typing import ColumnTypes


class DuckDBConnector(DatabaseConnector):
    """
    DuckDB 数据库连接器

    使用 duckdb 包连接 DuckDB 数据库。

    特性：
    - 高性能 OLAP 查询引擎
    - 支持所有 DatabaseConnector 接口
    - 支持多 schema
    - 支持原生表备注与列备注

    Example:
        with DuckDBConnector('data.duckdb') as conn:
            tables = conn.get_table_names()
            for table in tables:
                data = conn.get_table_data(table)
    """

    DB_TYPE = 'duckdb'
    REQUIRED_DEPENDENCIES: List[str] = ['duckdb']

    TYPE_TO_SQL: Dict[ColumnTypes, str] = {
        # 基础类型
        int: 'BIGINT',
        str: 'VARCHAR',
        float: 'DOUBLE',
        bool: 'BOOLEAN',
        bytes: 'BLOB',
        # 扩展类型（尽量使用 DuckDB 原生类型）
        datetime: 'TIMESTAMP',
        date: 'DATE',
        timedelta: 'INTERVAL',
        list: 'JSON',
        dict: 'JSON',
    }

    SQL_TO_TYPE: Dict[str, ColumnTypes] = {
        # 整数类型
        'BIGINT': int,
        'INTEGER': int,
        'INT': int,
        'SMALLINT': int,
        'TINYINT': int,
        'HUGEINT': int,
        'UBIGINT': int,
        'UINTEGER': int,
        'USMALLINT': int,
        'UTINYINT': int,
        'INT8': int,
        'INT4': int,
        'INT2': int,
        'INT1': int,
        'LONG': int,
        # 浮点类型
        'DOUBLE': float,
        'FLOAT': float,
        'REAL': float,
        'DECIMAL': float,
        'NUMERIC': float,
        # 字符串类型
        'VARCHAR': str,
        'TEXT': str,
        'CHAR': str,
        'BPCHAR': str,
        'STRING': str,
        # 二进制类型
        'BLOB': bytes,
        'BYTEA': bytes,
        # 布尔类型
        'BOOLEAN': bool,
        'BOOL': bool,
        # JSON 类型
        'JSON': dict,
        # 时间类型（用于外部 DuckDB 数据库类型推断）
        'TIMESTAMP': datetime,
        'TIMESTAMP WITH TIME ZONE': datetime,
        'TIMESTAMPTZ': datetime,
        'DATETIME': datetime,
        'DATE': date,
        'INTERVAL': timedelta,
        'TIME': str,  # Pytuck 暂不支持 time 类型，用 str
    }

    def __init__(self, db_path: str, options: DuckdbConnectorOptions):
        """
        初始化 DuckDB 连接器

        Args:
            db_path: DuckDB 数据库文件路径
            options: DuckDB 连接器配置选项
        """
        super().__init__(db_path, options)
        self.options: DuckdbConnectorOptions = options
        self.conn: Any = None  # duckdb.DuckDBPyConnection

    def connect(self) -> None:
        """连接到 DuckDB 数据库"""
        import duckdb

        conn = duckdb.connect(self.db_path, read_only=self.options.read_only)
        try:
            if self.options.threads is not None:
                threads = int(self.options.threads)
                conn.execute(f'SET threads = {threads}')

            if not self.options.read_only:
                conn.execute(
                    f'CREATE SCHEMA IF NOT EXISTS {self._quote_identifier(self.options.schema)}'
                )

            conn.execute(
                f'SET schema = {self._quote_string_literal(self.options.schema)}'
            )
        except Exception:
            conn.close()
            raise

        self.conn = conn

    def close(self) -> None:
        """关闭连接"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.conn is not None

    def get_table_names(self, exclude_system: bool = True) -> List[str]:
        """
        获取所有表名

        Args:
            exclude_system: 是否排除系统表和 Pytuck 元数据表（_pytuck_*）
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? AND table_type = 'BASE TABLE' "
            "ORDER BY table_name",
            [self.options.schema]
        )
        tables = [row[0] for row in result.fetchall()]

        if exclude_system:
            tables = [
                table_name for table_name in tables
                if not table_name.startswith('_pytuck_')
            ]

        return tables

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ? AND table_type = 'BASE TABLE'",
            [self.options.schema, table_name]
        )
        return result.fetchone() is not None

    def get_table_schema(self, table_name: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        获取表结构

        Returns:
            (columns, primary_key) 元组
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)

        result = self.conn.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? "
            "ORDER BY ordinal_position",
            [self.options.schema, table_name]
        )
        col_rows = result.fetchall()

        pk_columns: List[str] = []
        try:
            pk_result = self.conn.execute(
                "SELECT kcu.column_name "
                "FROM information_schema.key_column_usage kcu "
                "JOIN information_schema.table_constraints tc "
                "ON kcu.constraint_name = tc.constraint_name "
                "AND kcu.table_schema = tc.table_schema "
                "WHERE tc.table_schema = ? "
                "AND tc.table_name = ? "
                "AND tc.constraint_type = 'PRIMARY KEY' "
                "ORDER BY kcu.ordinal_position",
                [self.options.schema, table_name]
            )
            pk_columns = [row[0] for row in pk_result.fetchall()]
        except Exception:
            pass

        column_comments = self.get_column_comments(table_name)
        indexed_columns = self.get_indexed_columns(table_name)

        columns: List[Dict[str, Any]] = []
        primary_key: Optional[str] = pk_columns[0] if pk_columns else None

        for col_name, col_type_str, is_nullable in col_rows:
            col_type_upper = (col_type_str or '').upper()
            py_type: Type = str

            if 'JSON' in col_type_upper:
                py_type = self._infer_json_python_type(table_name, col_name)
            else:
                for sql_type, mapped_type in self.SQL_TO_TYPE.items():
                    if sql_type in col_type_upper:
                        py_type = mapped_type
                        break

            columns.append({
                'name': col_name,
                'type': py_type,
                'nullable': is_nullable == 'YES',
                'primary_key': col_name == primary_key,
                'comment': column_comments.get(col_name),
                'index': col_name in indexed_columns,
            })

        return columns, primary_key

    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表中所有数据"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)

        result = self.conn.execute(f'SELECT * FROM {self._qualified_table_name(table_name)}')
        col_names = [desc[0] for desc in result.description]
        return [dict(zip(col_names, row)) for row in result.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> Any:
        """执行 SQL 语句"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")
        return self.conn.execute(sql, list(params) if params else [])

    def executemany(self, sql: str, params_list: List[tuple]) -> None:
        """批量执行 SQL 语句"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")
        self.conn.executemany(sql, params_list)

    def create_table(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        primary_key: Optional[str]
    ) -> None:
        """创建表"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        col_defs: List[str] = []
        for col in columns:
            is_pk = col.get('primary_key', False)
            col_type = col['type']
            sql_type = self.TYPE_TO_SQL.get(col_type, 'VARCHAR')
            constraints: List[str] = []

            if is_pk:
                constraints.append('PRIMARY KEY')
            elif not col.get('nullable', True):
                constraints.append('NOT NULL')

            col_def = f'{self._quote_identifier(col["name"])} {sql_type}'
            if constraints:
                col_def += ' ' + ' '.join(constraints)

            col_defs.append(col_def)

        sql = f'CREATE TABLE {self._qualified_table_name(table_name)} ({", ".join(col_defs)})'
        self.conn.execute(sql)

    def drop_table(self, table_name: str) -> None:
        """删除表"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")
        self.conn.execute(f'DROP TABLE IF EXISTS {self._qualified_table_name(table_name)}')

    def insert_records(
        self,
        table_name: str,
        columns: List[str],
        records: List[Dict[str, Any]]
    ) -> None:
        """批量插入记录"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if not records:
            return

        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join([self._quote_identifier(column_name) for column_name in columns])
        sql = (
            f'INSERT INTO {self._qualified_table_name(table_name)} '
            f'({col_names}) VALUES ({placeholders})'
        )

        values_list: List[tuple] = []
        for record in records:
            values = []
            for column_name in columns:
                values.append(self._serialize_value(record.get(column_name)))
            values_list.append(tuple(values))

        self.conn.executemany(sql, values_list)

    def insert_records_fast(
        self,
        table_name: str,
        columns: List[str],
        records: List[Dict[str, Any]]
    ) -> None:
        """
        通过临时 CSV + COPY FROM 快速批量插入

        DuckDB 的 SQL INSERT 即使用 executemany 也较慢（OLAP 架构特性），
        而 COPY FROM CSV 能利用 DuckDB 的列式引擎高效加载数据。
        100k 条记录：executemany ~50s，COPY FROM CSV ~0.2s。

        Args:
            table_name: 表名
            columns: 列名列表（固定顺序）
            records: 数据字典列表
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if not records:
            return

        import csv
        import tempfile
        from pathlib import Path

        # 写入临时 CSV 文件
        temp_dir = Path(tempfile.gettempdir())
        csv_path = temp_dir / f'_pytuck_bulk_{id(self)}.csv'

        try:
            with open(str(csv_path), 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for record in records:
                    row = []
                    for col in columns:
                        value = self._serialize_value(record.get(col))
                        row.append(value)
                    writer.writerow(row)

            # 使用 COPY FROM 加载 CSV
            col_names = ', '.join([self._quote_identifier(c) for c in columns])
            self.conn.execute(
                f'COPY {self._qualified_table_name(table_name)} ({col_names}) '
                f"FROM '{csv_path}' (FORMAT CSV, HEADER FALSE, NULL_PADDING TRUE)"
            )
        finally:
            # 清理临时文件
            try:
                csv_path.unlink()
            except FileNotFoundError:
                pass

    def commit(self) -> None:
        """提交事务"""
        if self.conn is not None:
            self.conn.commit()

    def set_table_comment(self, table_name: str, comment: Optional[str]) -> None:
        """设置表备注"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if comment is None:
            sql = f'COMMENT ON TABLE {self._qualified_table_name(table_name)} IS NULL'
        else:
            sql = (
                f'COMMENT ON TABLE {self._qualified_table_name(table_name)} '
                f'IS {self._quote_string_literal(comment)}'
            )
        self.conn.execute(sql)

    def set_column_comment(
        self,
        table_name: str,
        column_name: str,
        comment: Optional[str]
    ) -> None:
        """设置列备注"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if comment is None:
            sql = (
                f'COMMENT ON COLUMN {self._qualified_column_name(table_name, column_name)} IS NULL'
            )
        else:
            sql = (
                f'COMMENT ON COLUMN {self._qualified_column_name(table_name, column_name)} '
                f'IS {self._quote_string_literal(comment)}'
            )
        self.conn.execute(sql)

    def get_table_comment(self, table_name: str) -> Optional[str]:
        """读取表备注"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            "SELECT comment FROM duckdb_tables() "
            "WHERE schema_name = ? AND table_name = ?",
            [self.options.schema, table_name]
        )
        row = result.fetchone()
        if row is None:
            return None
        return row[0]

    def get_column_comments(self, table_name: str) -> Dict[str, Optional[str]]:
        """读取列备注"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            "SELECT column_name, comment FROM duckdb_columns() "
            "WHERE schema_name = ? AND table_name = ? "
            "ORDER BY column_index",
            [self.options.schema, table_name]
        )
        return {row[0]: row[1] for row in result.fetchall()}

    def get_indexed_columns(self, table_name: str) -> Set[str]:
        """读取表上已存在的单列索引列名"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            "SELECT expressions FROM duckdb_indexes() "
            "WHERE schema_name = ? AND table_name = ? AND is_primary = FALSE",
            [self.options.schema, table_name]
        )

        indexed_columns: Set[str] = set()
        for row in result.fetchall():
            expressions = row[0]
            if not expressions:
                continue
            try:
                parsed = ast.literal_eval(expressions)
            except (ValueError, SyntaxError):
                continue
            if not isinstance(parsed, list) or len(parsed) != 1:
                continue
            expression = parsed[0]
            if not isinstance(expression, str):
                continue
            indexed_columns.add(self._unquote_identifier(expression))

        return indexed_columns

    def get_next_id(self, table_name: str, pk_column: str) -> int:
        """根据当前最大整数主键推导下一个 ID"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            f'SELECT COALESCE(MAX({self._quote_identifier(pk_column)}), 0) + 1 '
            f'FROM {self._qualified_table_name(table_name)}'
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return 1
        return int(row[0])

    # ==========================================================================
    # 原生 SQL CRUD 实现
    # ==========================================================================

    def supports_crud(self) -> bool:
        """DuckDB 支持直接 CRUD 操作"""
        return True

    def insert_row(
        self,
        table_name: str,
        data: Dict[str, Any],
        pk_column: str
    ) -> Any:
        """
        插入一行数据

        Args:
            table_name: 表名
            data: 列名到值的映射
            pk_column: 主键列名

        Returns:
            插入记录的主键值
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        has_explicit_pk = pk_column and pk_column in data and data[pk_column] is not None
        columns = [name for name in data.keys() if name != pk_column or has_explicit_pk]
        col_names = ', '.join([self._quote_identifier(column_name) for column_name in columns])
        placeholders = ', '.join(['?' for _ in columns])

        params = [self._serialize_value(data[column_name]) for column_name in columns]

        if has_explicit_pk:
            sql = (
                f'INSERT INTO {self._qualified_table_name(table_name)} '
                f'({col_names}) VALUES ({placeholders})'
            )
            self.conn.execute(sql, params)
            return data[pk_column]

        sql = (
            f'INSERT INTO {self._qualified_table_name(table_name)} '
            f'({col_names}) VALUES ({placeholders}) '
            f'RETURNING {self._quote_identifier(pk_column)}'
        )
        result = self.conn.execute(sql, params)
        row = result.fetchone()
        return row[0] if row else None

    def update_row(
        self,
        table_name: str,
        pk_column: str,
        pk_value: Any,
        data: Dict[str, Any]
    ) -> int:
        """
        更新一行数据

        Args:
            table_name: 表名
            pk_column: 主键列名
            pk_value: 主键值
            data: 要更新的列名到值的映射

        Returns:
            影响的行数
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        set_clause = ', '.join([f'{self._quote_identifier(key)} = ?' for key in data.keys()])
        sql = (
            f'UPDATE {self._qualified_table_name(table_name)} '
            f'SET {set_clause} WHERE {self._quote_identifier(pk_column)} = ?'
        )

        params = [self._serialize_value(value) for value in data.values()]
        params.append(self._serialize_value(pk_value))

        result = self.conn.execute(sql, params)
        rowcount = getattr(result, 'rowcount', -1)
        return rowcount if isinstance(rowcount, int) and rowcount >= 0 else 0

    def delete_row(
        self,
        table_name: str,
        pk_column: str,
        pk_value: Any
    ) -> int:
        """
        删除一行数据

        Args:
            table_name: 表名
            pk_column: 主键列名
            pk_value: 主键值

        Returns:
            影响的行数
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        sql = (
            f'DELETE FROM {self._qualified_table_name(table_name)} '
            f'WHERE {self._quote_identifier(pk_column)} = ?'
        )
        result = self.conn.execute(sql, [self._serialize_value(pk_value)])
        rowcount = getattr(result, 'rowcount', -1)
        return rowcount if isinstance(rowcount, int) and rowcount >= 0 else 0

    def select_by_pk(
        self,
        table_name: str,
        pk_column: str,
        pk_value: Any,
        columns: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        按主键查询一行

        Args:
            table_name: 表名
            pk_column: 主键列名
            pk_value: 主键值
            columns: 要查询的列名列表，None 表示所有列

        Returns:
            匹配的记录字典，未找到返回 None
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if columns:
            cols = ', '.join([self._quote_identifier(column_name) for column_name in columns])
        else:
            cols = '*'

        sql = (
            f'SELECT {cols} FROM {self._qualified_table_name(table_name)} '
            f'WHERE {self._quote_identifier(pk_column)} = ?'
        )
        result = self.conn.execute(sql, [self._serialize_value(pk_value)])
        row = result.fetchone()

        if row is None:
            return None

        col_names = [desc[0] for desc in result.description]
        return dict(zip(col_names, row))

    def query_rows(
        self,
        table_name: str,
        where_clause: Optional[str] = None,
        params: Tuple[Any, ...] = (),
        columns: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        条件查询多行

        Args:
            table_name: 表名
            where_clause: WHERE 子句（不含 WHERE 关键字）
            params: WHERE 子句的参数
            columns: 要查询的列名列表，None 表示所有列
            order_by: ORDER BY 子句（不含 ORDER BY 关键字）
            limit: 最大返回行数
            offset: 跳过的行数

        Returns:
            记录字典列表
        """
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        if columns:
            cols = ', '.join([self._quote_identifier(column_name) for column_name in columns])
        else:
            cols = '*'

        sql = f'SELECT {cols} FROM {self._qualified_table_name(table_name)}'

        if where_clause:
            sql += f' WHERE {where_clause}'
        if order_by:
            sql += f' ORDER BY {order_by}'
        if limit is not None:
            sql += f' LIMIT {limit}'
        if offset is not None:
            sql += f' OFFSET {offset}'

        result = self.conn.execute(sql, list(params) if params else [])
        col_names = [desc[0] for desc in result.description]
        return [dict(zip(col_names, row)) for row in result.fetchall()]

    def begin_transaction(self) -> None:
        """开始事务"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")
        self.conn.begin()

    def rollback_transaction(self) -> None:
        """回滚事务"""
        if self.conn is not None:
            self.conn.rollback()

    def commit_transaction(self) -> None:
        """提交事务"""
        if self.conn is not None:
            self.conn.commit()

    def _infer_json_python_type(self, table_name: str, column_name: str) -> ColumnTypes:
        """根据现有 JSON 数据推断列应映射为 list 还是 dict"""
        if self.conn is None:
            raise DatabaseConnectionError("数据库未连接，请先调用 connect()")

        result = self.conn.execute(
            f'SELECT json_type({self._quote_identifier(column_name)}) '
            f'FROM {self._qualified_table_name(table_name)} '
            f'WHERE {self._quote_identifier(column_name)} IS NOT NULL '
            f'LIMIT 1'
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return dict
        if row[0] == 'ARRAY':
            return list
        return dict

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """使用标准 SQL 双引号引用标识符"""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _quote_string_literal(value: str) -> str:
        """引用 SQL 字符串字面量"""
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def _qualified_table_name(self, table_name: str) -> str:
        """返回带 schema 的表名"""
        return (
            f'{self._quote_identifier(self.options.schema)}.'
            f'{self._quote_identifier(table_name)}'
        )

    def _qualified_column_name(self, table_name: str, column_name: str) -> str:
        """返回带 schema 的列名"""
        return f'{self._qualified_table_name(table_name)}.{self._quote_identifier(column_name)}'

    @staticmethod
    def _unquote_identifier(identifier: str) -> str:
        """将 DuckDB catalog 中的引用标识符还原为原始名称"""
        if identifier.startswith('"') and identifier.endswith('"'):
            return identifier[1:-1].replace('""', '"')
        return identifier

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """
        序列化值为 DuckDB 兼容格式

        Args:
            value: 要序列化的值

        Returns:
            DuckDB 兼容的值
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (datetime, date, timedelta)):
            return value

        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)

        return value
