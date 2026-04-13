from pathlib import Path
from typing import Type

from pytuck import Column, PureBaseModel, Session, Storage, declarative_base, insert
from pytuck.common.options import BinaryBackendOptions


FIXTURE_DIR = Path(__file__).parent / "ptk5"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def build_plain_users() -> None:
    db_path = FIXTURE_DIR / "basic_users.pytuck"
    db = Storage(file_path=str(db_path), engine="pytuck")
    Base: Type[PureBaseModel] = declarative_base(db)

    class User(Base):
        __tablename__ = "users"
        id = Column(int, primary_key=True)
        name = Column(str, index=True)
        age = Column(int)

    session = Session(db)
    session.execute(insert(User).values(name="Alice", age=20))
    session.execute(insert(User).values(name="Bob", age=30))
    session.commit()
    db.flush()
    db.close()


def build_encrypted(level: str) -> None:
    db_path = FIXTURE_DIR / f"encrypted_{level}.pytuck"
    db = Storage(
        file_path=str(db_path),
        engine="pytuck",
        backend_options=BinaryBackendOptions(encryption=level, password="secret123"),
    )
    db.create_table(
        "users",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="name"),
        ],
    )
    db.insert("users", {"name": f"{level}-user"})
    db.flush()
    db.close()


if __name__ == "__main__":
    build_plain_users()
    for level in ("low", "medium", "high"):
        build_encrypted(level)
