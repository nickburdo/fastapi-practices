from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from books import services
from books.exceptions import BookNotFoundError
from books.models import BookModel
from books.schemas import BookCreateSchema, BookSchema
from shared.database.session import SessionDep

book_router = APIRouter(prefix="/books", tags=["Books"])


@book_router.get("/", summary="List of books", response_model=list[BookSchema])
async def read_books(session: SessionDep) -> Sequence[BookModel]:
    return await services.get_books(session=session)


@book_router.get(
    "/{book_id}",
    summary="Get a book by ID",
    response_model=BookSchema,
    responses={404: {"description": "Book not found"}},
)
async def read_book(
    book_id: Annotated[int, Path(gt=0)], session: SessionDep
) -> BookModel:
    try:
        return await services.get_book(book_id=book_id, session=session)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        ) from None


@book_router.post(
    "/",
    summary="Create a new book",
    response_model=BookSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_book(data: BookCreateSchema, session: SessionDep) -> BookModel:
    return await services.add_book(data=data, session=session)
