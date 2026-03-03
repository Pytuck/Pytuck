"""
测试 CSV 后端 field_size_limit 选项
"""

import json
import zipfile

import pytest

from pytuck.common.options import CsvBackendOptions
from pytuck.common.exceptions import SerializationError, ValidationError
from pytuck.backends.backend_csv import CSVBackend


def _build_csv_zip(path, table_name, field_size):
    """构建包含大字段的 CSV ZIP 文件"""
    # 构造 metadata
    metadata = {
        'format_version': '1.0',
        'tables': {
            table_name: {
                'primary_key': 'id',
                'next_id': 2,
                'columns': [
                    {'name': 'id', 'type': 'int', 'nullable': False, 'primary_key': True, 'index': False},
                    {'name': 'data', 'type': 'str', 'nullable': True, 'primary_key': False, 'index': False}
                ]
            }
        }
    }

    # 构造超大字段的 CSV 内容
    large_value = 'x' * field_size
    csv_content = f'id,data\n1,"{large_value}"\n'

    with zipfile.ZipFile(str(path), 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('_metadata.json', json.dumps(metadata).encode('utf-8'))
        zf.writestr(f'{table_name}.csv', csv_content.encode('utf-8-sig'))


class TestCsvFieldSizeLimit:
    """CSV field_size_limit 选项测试"""

    def test_large_field_without_limit_fails(self, tmp_path):
        """字段超过默认限制（131072）时加载失败"""
        zip_path = tmp_path / 'big.csv.zip'
        _build_csv_zip(zip_path, 'bigtable', 200_000)

        options = CsvBackendOptions()  # field_size_limit 默认 None
        backend = CSVBackend(str(zip_path), options)

        with pytest.raises(SerializationError, match='field larger than field limit'):
            backend.load()

    def test_large_field_with_limit_succeeds(self, tmp_path):
        """设置 field_size_limit 后能成功加载大字段"""
        zip_path = tmp_path / 'big.csv.zip'
        field_size = 200_000
        _build_csv_zip(zip_path, 'bigtable', field_size)

        options = CsvBackendOptions(field_size_limit=300_000)
        backend = CSVBackend(str(zip_path), options)

        tables = backend.load()
        assert 'bigtable' in tables
        table = tables['bigtable']
        assert 1 in table.data
        assert len(table.data[1]['data']) == field_size

    def test_normal_field_without_limit(self, tmp_path):
        """普通大小字段在默认限制下正常加载"""
        zip_path = tmp_path / 'normal.csv.zip'
        _build_csv_zip(zip_path, 'normaltable', 1000)

        options = CsvBackendOptions()
        backend = CSVBackend(str(zip_path), options)

        tables = backend.load()
        assert 'normaltable' in tables
        assert 1 in tables['normaltable'].data
        assert len(tables['normaltable'].data[1]['data']) == 1000

    def test_field_size_limit_restores_after_load(self, tmp_path):
        """加载完成后 csv.field_size_limit 恢复为原值"""
        import csv

        zip_path = tmp_path / 'big.csv.zip'
        _build_csv_zip(zip_path, 'bigtable', 200_000)

        original_limit = csv.field_size_limit()

        options = CsvBackendOptions(field_size_limit=300_000)
        backend = CSVBackend(str(zip_path), options)
        backend.load()

        assert csv.field_size_limit() == original_limit

    def test_field_size_limit_restores_on_error(self, tmp_path):
        """加载失败时 csv.field_size_limit 也能恢复为原值"""
        import csv

        zip_path = tmp_path / 'big.csv.zip'
        _build_csv_zip(zip_path, 'bigtable', 200_000)

        original_limit = csv.field_size_limit()

        # 设置一个仍然不够大的 limit
        options = CsvBackendOptions(field_size_limit=100_000)
        backend = CSVBackend(str(zip_path), options)

        with pytest.raises(SerializationError):
            backend.load()

        assert csv.field_size_limit() == original_limit


class TestCsvFieldSizeLimitValidation:
    """field_size_limit 参数校验测试"""

    def test_negative_value_raises(self):
        """负数应报错"""
        with pytest.raises(ValidationError):
            CsvBackendOptions(field_size_limit=-1)

    def test_zero_value_raises(self):
        """0 应报错"""
        with pytest.raises(ValidationError):
            CsvBackendOptions(field_size_limit=0)

    def test_none_is_valid(self):
        """None 是有效值（使用默认限制）"""
        opts = CsvBackendOptions(field_size_limit=None)
        assert opts.field_size_limit is None

    def test_positive_int_is_valid(self):
        """正整数是有效值"""
        opts = CsvBackendOptions(field_size_limit=500_000)
        assert opts.field_size_limit == 500_000
