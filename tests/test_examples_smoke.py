from pathlib import Path

import pytest



EXAMPLES_README = Path("examples/README.md")


def test_examples_readme_documents_baseline_groups() -> None:
    content = EXAMPLES_README.read_text(encoding="utf-8")

    assert "## 推荐起步示例" in content
    assert "`session_api_demo.py`" in content
    assert "`active_record_demo.py`" in content
    assert "## 发布前建议验证的示例" in content
    assert "uv run python examples/session_api_demo.py" in content
    assert "uv run python examples/active_record_demo.py" in content
    assert "## 补充示例" in content
    assert "`backend_options_demo.py`" in content


def test_session_api_demo_runs(capsys: pytest.CaptureFixture[str]) -> None:
    from examples import session_api_demo

    session_api_demo.main()
    output = capsys.readouterr().out

    assert "Pytuck Session + Statement API 完整示例" in output
    assert "✓ Session 已关闭" in output


def test_active_record_demo_runs(capsys: pytest.CaptureFixture[str]) -> None:
    from examples import active_record_demo

    active_record_demo.main()
    output = capsys.readouterr().out

    assert "Pytuck Active Record 模式示例" in output
    assert "✓ 数据库已关闭" in output


def test_pytuck_default_demo_runs(capsys: pytest.CaptureFixture[str]) -> None:
    from examples import backend_options_demo

    backend_options_demo.demo_pytuck_default()
    output = capsys.readouterr().out

    assert "Pytuck 引擎演示（默认选项）" in output
    assert "配置选项: 无（使用默认设置）" in output
