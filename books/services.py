from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from books import repositories
from books.models import BookModel
from books.schemas import BookCreateSchema


async def get_books(session: AsyncSession) -> Sequence[BookModel]:
    return await repositories.get_all_books(session=session)


async def add_book(data: BookCreateSchema, session: AsyncSession) -> BookModel:
    new_book = BookModel(**data.model_dump())
    book = await repositories.add_book(new_book=new_book, session=session)
    await session.commit()
    return book
