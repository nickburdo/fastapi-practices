from sqlalchemy import String, false
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.models import Base


class UserModel(Base):
    __tablename__ = "users"
    # Never reuse ids of deleted users: a JWT stores the user id
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=false())
