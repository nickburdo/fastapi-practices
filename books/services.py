from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from books import repositories
from books.exceptions import BookNotFoundError
from books.models import BookModel
from books.schemas import BookCreateSchema


async def get_books(session: AsyncSession) -> Sequence[BookModel]:
    return await repositories.get_all_books(session=session)


async def get_book(book_id: int, session: AsyncSession) -> BookModel:
    book = await repositories.get_book_by_id(book_id=book_id, session=session)
    if book is None:
        raise BookNotFoundError(book_id)
    return book


async def add_book(data: BookCreateSchema, session: AsyncSession) -> BookModel:
    new_book = BookModel(**data.model_dump())
    book = await repositories.add_book(new_book=new_book, session=session)
    await session.commit()
    return book
