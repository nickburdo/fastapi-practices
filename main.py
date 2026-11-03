from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from files.routes import files_router
from shared.auth import auth
from shared.config import settings
from shared.database.session import engine
from users.routes import auth_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)  # Register error handlers for proper responses


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(book_router)
app.include_router(files_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
