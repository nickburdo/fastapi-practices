from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from books.models import BookModel


async def get_all_books(session: AsyncSession) -> Sequence[BookModel]:
    query = select(BookModel)
    result = await session.execute(query)
    return result.scalars().all()


async def add_book(new_book: BookModel, session: AsyncSession) -> BookModel:
    session.add(new_book)
    await session.flush()
    return new_book
