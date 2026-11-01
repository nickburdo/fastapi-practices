from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from books.models import BookModel


async def get_all_books(session: AsyncSession) -> Sequence[BookModel]:
    query = select(BookModel).order_by(BookModel.id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_book_by_id(book_id: int, session: AsyncSession) -> BookModel | None:
    return await session.get(BookModel, book_id)


async def add_book(new_book: BookModel, session: AsyncSession) -> BookModel:
    session.add(new_book)
    await session.flush()
    return new_book
