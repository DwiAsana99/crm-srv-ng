from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, TIMESTAMP
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR
from app.db.session import engine  # hanya agar mypy tahu dialek; tidak dipakai langsung
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase): ...

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(VARCHAR(190), index=True)
    password: Mapped[str] = mapped_column(VARCHAR(255))
    role_id: Mapped[int | None] = mapped_column(BIGINT(unsigned=True), nullable=True)
    userable_id: Mapped[str | None] = mapped_column(VARCHAR(20), nullable=True)
    userable_type: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    created_at: Mapped[str | None] = mapped_column(TIMESTAMP, nullable=True)
    updated_at: Mapped[str | None] = mapped_column(TIMESTAMP, nullable=True)
    token_fcm: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
