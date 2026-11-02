from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from shared.auth import auth
from shared.database.session import SessionDep
from users import services
from users.dependencies import CurrentAdminDep, CurrentUserDep, get_current_user
from users.exceptions import (
    InvalidCredentialsError,
    SelfDeletionError,
    UsernameTakenError,
    UserNotFoundError,
)
from users.models import UserModel
from users.schema import TokenSchema, UserCredentialsSchema, UserSchema

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
users_router = APIRouter(
    prefix="/users", tags=["Users"], dependencies=[Depends(get_current_user)]
)


def create_token(user: UserModel) -> TokenSchema:
    return TokenSchema(access_token=auth.create_access_token(uid=str(user.id)))


@auth_router.post(
    "/register",
    summary="Register a new user and log in",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Username already taken"}},
)
async def register(data: UserCredentialsSchema, session: SessionDep) -> TokenSchema:
    try:
        user = await services.register_user(data=data, session=session)
    except UsernameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        ) from None
    return create_token(user)


@auth_router.post(
    "/login",
    summary="Log in with username and password",
    responses={401: {"description": "Invalid username or password"}},
)
async def login(data: UserCredentialsSchema, session: SessionDep) -> TokenSchema:
    try:
        user = await services.authenticate_user(data=data, session=session)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from None
    return create_token(user=user)


@users_router.get(
    "/",
    summary="List of users",
    response_model=list[UserSchema],
)
async def read_user(session: SessionDep) -> Sequence[UserModel]:
    return await services.get_users(session=session)


@users_router.get(
    "/me",
    summary="Current user",
    response_model=UserSchema,
)
async def read_current_user(current_user: CurrentUserDep) -> UserModel:
    return current_user


@users_router.delete(
    "/{user_id}",
    summary="Delete a user (admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "Admin cannot delete themselves"},
        403: {"description": "Admin rights required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: Annotated[int, Path(gt=0)],
    current_admin: CurrentAdminDep,
    session: SessionDep,
) -> None:
    try:
        await services.delete_user(
            user_id=user_id, current_user=current_admin, session=session
        )
    except SelfDeletionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
