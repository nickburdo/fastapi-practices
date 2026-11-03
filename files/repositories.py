from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from files.models import FileModel


async def get_files(owner_id: int | None, session: AsyncSession) -> Sequence[FileModel]:
    query = select(FileModel).order_by(FileModel.id)
    if owner_id is not None:
        query = query.where(FileModel.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_file_by_id(file_id: int, session: AsyncSession) -> FileModel | None:
    return await session.get(FileModel, file_id)


async def add_files(
    new_files: list[FileModel], session: AsyncSession
) -> list[FileModel]:
    session.add_all(new_files)
    await session.flush()
    return new_files


async def delete_file(file: FileModel, session: AsyncSession) -> None:
    await session.delete(file)
    await session.flush()
