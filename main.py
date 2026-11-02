from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel

from books.routes import book_router
from shared import auth
from shared.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)  # Register error handlers for proper responses


class UserLoginSchema(BaseModel):
    username: str
    password: str


@app.post("/login", tags=["Authentication555"])
def login(data: UserLoginSchema, response: Response):
    if data.username == "test" and data.password == "test":
        token = auth.create_access_token(uid=data.username)
        response.set_cookie(key="access_token", value=token, httponly=True)
        return {"access_token": token}
    raise HTTPException(401, detail="Invalid credentials")


@app.get("/protected", dependencies=[Depends(auth.access_token_required)])
def protected():
    return {"message": "Hello, FastAPI World"}


app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
