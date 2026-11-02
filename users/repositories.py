from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import UserModel


async def get_all_users(session: AsyncSession) -> Sequence[UserModel]:
    query = select(UserModel).order_by(UserModel.id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_user_by_id(user_id: int, session: AsyncSession) -> UserModel | None:
    return await session.get(UserModel, user_id)


async def get_user_by_username(
    username: str, session: AsyncSession
) -> UserModel | None:
    query = select(UserModel).where(UserModel.username == username)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def add_user(new_user: UserModel, session: AsyncSession) -> UserModel:
    session.add(new_user)
    await session.flush()
    return new_user


async def delete_user(user: UserModel, sesion: AsyncSession) -> None:
    await sesion.delete(user)
    await sesion.flush()
