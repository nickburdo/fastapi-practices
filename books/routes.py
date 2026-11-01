from collections.abc import Sequence

from fastapi import APIRouter, status

from books import services
from books.models import BookModel
from books.schemas import BookCreateSchema, BookSchema
from shared.database.session import SessionDep

book_router = APIRouter(prefix="/books", tags=["Books"])


@book_router.get("/", summary="List of books", response_model=list[BookSchema])
async def read_books(session: SessionDep) -> Sequence[BookModel]:
    return await services.get_books(session=session)


# @app.get("/{book_id}", summary="Get a book by ID")
# def read_book(book_id: int):
#     for book in books:
#         if book["id"] == book_id:
#             return book
#     raise HTTPException(status_code=404, detail="Book not found")
#


@book_router.post(
    "/",
    summary="Create a new book",
    response_model=BookSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_book(data: BookCreateSchema, session: SessionDep) -> BookModel:
    return await services.add_book(data=data, session=session)
