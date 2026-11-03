from collections.abc import Sequence

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from files import repositories, storage
from files.exceptions import StoredFileNotFoundError
from files.models import FileModel
from files.validation import check_uploads
from users.models import UserModel


async def get_files(user: UserModel, session: AsyncSession) -> Sequence[FileModel]:
    owner_id = None if user.is_admin else user.id
    return await repositories.get_files(owner_id=owner_id, session=session)


async def _get_accessible_file(
    file_id: int, user: UserModel, session: AsyncSession
) -> FileModel:
    file = await repositories.get_file_by_id(file_id=file_id, session=session)
    # Someone else's file looks exactly like a missing one
    if file is None or (not user.is_admin and file.owner_id != user.id):
        raise StoredFileNotFoundError(file_id)
    return file


async def get_file(file_id: int, user: UserModel, session: AsyncSession) -> FileModel:
    file = await _get_accessible_file(file_id=file_id, user=user, session=session)
    if not await storage.exists(file.stored_name):
        raise StoredFileNotFoundError(file_id)
    return file


async def delete_file(file_id: int, user: UserModel, session: AsyncSession) -> None:
    file = await _get_accessible_file(file_id=file_id, user=user, session=session)
    await repositories.delete_file(file=file, session=session)
    await session.commit()
    # Disk last: if the commit fails, the file is still there for its record
    await storage.delete(file.stored_name)


async def upload_files(
    uploads: list[UploadFile], owner: UserModel, session: AsyncSession
) -> list[FileModel]:
    # Check every file before writing anything: one bad file rejects the request
    checked_uploads = check_uploads(uploads)

    stored_names: list[str] = []
    new_files: list[FileModel] = []
    try:
        for checked in checked_uploads:
            stored_name = storage.make_stored_name(checked.original_name)
            stored_names.append(stored_name)
            await storage.save(checked.file, stored_name)
            new_files.append(
                FileModel(
                    owner_id=owner.id,
                    original_name=checked.original_name,
                    stored_name=stored_name,
                    content_type=checked.content_type,
                    size=checked.size,
                )
            )
        files = await repositories.add_files(new_files=new_files, session=session)
        await session.commit()
    except Exception:
        # Do not leave files on disk without database records
        for stored_name in stored_names:
            await storage.delete(stored_name)
        raise
    return files
