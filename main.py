from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from shared.auth import auth
from shared.database.session import engine
from users.routes import auth_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)  # Register error handlers for proper responses


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
