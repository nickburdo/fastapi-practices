from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from shared.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
