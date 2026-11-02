from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import current_user

from users import repositories
from users.exceptions import (
    InvalidCredentialsError,
    SelfDeletionError,
    UsernameTakenError,
    UserNotFoundError,
)
from users.models import UserModel
from users.schema import UserCredentialsSchema
from users.security import DUMMY_HASH, hash_password, verify_password


async def get_users(session: AsyncSession) -> Sequence[UserModel]:
    return await repositories.get_all_users(session)


async def get_user(user_id: int, session: AsyncSession) -> UserModel:
    user = await repositories.get_user_by_id(user_id=user_id, session=session)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


async def register_user(
    data: UserCredentialsSchema, session: AsyncSession
) -> UserModel:
    existing_user = await repositories.get_user_by_username(
        username=data.username, session=session
    )
    if existing_user is not None:
        raise UsernameTakenError(data.username)
    new_user = UserModel(
        username=data.username, hashed_password=hash_password(data.password)
    )
    user = await repositories.add_user(new_user=new_user, session=session)
    await session.commit()
    return user


async def authenticate_user(
    data: UserCredentialsSchema, session: AsyncSession
) -> UserModel:
    user = await repositories.get_user_by_username(
        username=data.username, session=session
    )
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise InvalidCredentialsError()
    if not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


async def delete_user(user_id: int, session: AsyncSession) -> None:
    if user_id == current_user.id:
        raise SelfDeletionError(user_id)
    user = await get_user(user_id=user_id, session=session)
    await repositories.delete_user(user=user, session=session)
    await session.commit()
