from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse

from files import services, storage
from files.exceptions import (
    FileTooLargeError,
    StoredFileNotFoundError,
    UnsupportedFileTypeError,
    UploadValidationError,
)
from files.models import FileModel
from files.schemas import FileSchema
from shared.database.session import SessionDep
from users.dependencies import CurrentUserDep

files_router = APIRouter(prefix="/files", tags=["Files"])


@files_router.post(
    "/",
    summary="Upload one or more files",
    response_model=list[FileSchema],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Too many files, empty file or too long name"},
        413: {"description": "File is too large"},
        415: {"description": "Unsupported file type"},
    },
)
async def upload_files(
    uploaded_files: Annotated[
        list[UploadFile],
        # format=binary makes Swagger UI show file pickers
        File(json_schema_extra={"items": {"type": "string", "format": "binary"}}),
    ],
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[FileModel]:
    try:
        return await services.upload_files(
            uploads=uploaded_files, owner=current_user, session=session
        )
    # Subclasses first: UploadValidationError catches everything else
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from None
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from None
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from None


@files_router.get(
    "/", summary="List of my files (admin: all files)", response_model=list[FileSchema]
)
async def read_files(
    current_user: CurrentUserDep, session: SessionDep
) -> Sequence[FileModel]:
    return await services.get_files(user=current_user, session=session)


@files_router.get(
    "/{file_id}",
    summary="Download a file by ID",
    response_class=FileResponse,
    responses={404: {"description": "File not found"}},
)
async def download_file(
    file_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUserDep,
    session: SessionDep,
) -> FileResponse:
    try:
        file = await services.get_file(
            file_id=file_id, user=current_user, session=session
        )
    except StoredFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        ) from None
    # filename= makes the browser download it under the original name (attachment)
    return FileResponse(
        storage.path_for(file.stored_name),
        media_type=file.content_type,
        filename=file.original_name,
    )


@files_router.delete(
    "/{file_id}",
    summary="Delete a file by ID",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "File not found"}},
)
async def delete_file(
    file_id: Annotated[int, Path(gt=0)],
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    try:
        await services.delete_file(file_id=file_id, user=current_user, session=session)
    except StoredFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        ) from None
