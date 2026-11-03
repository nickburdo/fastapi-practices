from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from books.routes import book_router
from shared.auth import auth
from shared.database.session import engine
from users.routes import auth_router, users_router

UPLOAD_DIR = Path(__file__).parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)  # Register error handlers for proper responses


@app.post("/files")
async def upload_file(uploaded_file: UploadFile):
    file = uploaded_file.file
    filename = Path(uploaded_file.filename or "uploaded_file").name
    destination = UPLOAD_DIR / filename
    with open(destination, "wb") as f:
        f.write(file.read())

    return {"filename": f"{filename} is uploaded"}


@app.post("/multiple-files")
async def upload_multiple_files(
    uploaded_files: Annotated[
        list[UploadFile],
        # format=binary makes Swagger UI show file pickers
        File(json_schema_extra={"items": {"type": "string", "format": "binary"}}),
    ],
):
    for uploaded_file in uploaded_files:
        file = uploaded_file.file
        filename = Path(uploaded_file.filename or "uploaded_file").name
        destination = UPLOAD_DIR / filename
        with open(destination, "wb") as f:
            f.write(file.read())

    return {"filename": f"{len(uploaded_files)} files is uploaded"}


@app.get("/files/{filename}")
async def get_file(filename: str):
    file_path = UPLOAD_DIR / Path(filename).name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
