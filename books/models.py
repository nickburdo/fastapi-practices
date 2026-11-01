from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.models import Base


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
