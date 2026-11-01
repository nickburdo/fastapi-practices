from fastapi import FastAPI

from books.routes import book_router
from shared.database.models import Base
from shared.database.session import engine

app = FastAPI()


@app.post("/setup-database", summary="Setup the database", tags=["Database"])
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"message": "Database setup complete"}


app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
