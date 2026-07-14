"""Ren'Py 等受限 Python 环境的 Pytuck 零依赖核心 smoke。"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Type

from pytuck import Column, PureBaseModel, Session, Storage, declarative_base, insert, select, update


def run_smoke(database_path: str | Path) -> dict[str, object]:
    """执行一次可重复运行的写入、持久化和重开验证。"""
    path = Path(database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    db = Storage(file_path=path, engine="pytuck", auto_flush=True)
    Base: Type[PureBaseModel] = declarative_base(db)

    class SaveSlot(Base):
        __tablename__ = "save_slots"

        id = Column(int, primary_key=True)
        name = Column(str, nullable=False, index=True)
        launch_count = Column(int, nullable=False, default=0)

    session = Session(db)
    current = session.execute(select(SaveSlot).filter_by(name="renpy-smoke")).first()
    if current is None:
        session.execute(insert(SaveSlot).values(name="renpy-smoke", launch_count=1))
    else:
        session.execute(
            update(SaveSlot)
            .where(SaveSlot.id == current.id)
            .values(launch_count=current.launch_count + 1)
        )
    session.commit()
    session.close()
    db.close()

    reopened = Storage(file_path=path, engine="pytuck")
    ReopenedBase: Type[PureBaseModel] = declarative_base(reopened)

    class ReopenedSaveSlot(ReopenedBase):
        __tablename__ = "save_slots"

        id = Column(int, primary_key=True)
        name = Column(str, nullable=False, index=True)
        launch_count = Column(int, nullable=False, default=0)

    reopened_session = Session(reopened)
    saved = reopened_session.execute(
        select(ReopenedSaveSlot).filter_by(name="renpy-smoke")
    ).one()
    result: dict[str, object] = {
        "name": saved.name,
        "launch_count": saved.launch_count,
        "database_path": str(path),
    }
    reopened_session.close()
    reopened.close()
    return result


def main() -> None:
    """在普通 CPython 中运行独立 smoke。"""
    with TemporaryDirectory(prefix="pytuck-renpy-smoke-") as temp_dir:
        result = run_smoke(Path(temp_dir) / "renpy-smoke.pytuck")
        print(f"Pytuck Ren'Py smoke 通过：{result}")


if __name__ == "__main__":
    main()
