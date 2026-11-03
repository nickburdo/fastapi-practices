from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from files.exceptions import (
    EmptyFileError,
    FileNameTooLongError,
    FileTooLargeError,
    TooManyFilesError,
    UnsupportedFileTypeError,
)
from shared.config import settings

# Extension -> the only Content-Type accepted with it.
# SVG is left out on purpose: it can contain JavaScript.
ALLOWED_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_NAME_LENGTH = 255  # matches FileModel.original_name


@dataclass(frozen=True)
class CheckedUpload:
    original_name: str
    content_type: str
    size: int
    file: BinaryIO


def check_upload(upload: UploadFile) -> CheckedUpload:
    # Client-supplied name without any directory parts
    name = Path(upload.filename or "").name
    if len(name) > MAX_NAME_LENGTH:
        raise FileNameTooLongError(MAX_NAME_LENGTH)

    # "text/plain; charset=utf-8" -> "text/plain"
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if ALLOWED_TYPES.get(Path(name).suffix.lower()) != content_type:
        raise UnsupportedFileTypeError(name)

    size = upload.size or 0
    if size == 0:
        raise EmptyFileError(name)
    if size > settings.max_upload_size:
        raise FileTooLargeError(name, settings.max_upload_size)

    return CheckedUpload(
        original_name=name, content_type=content_type, size=size, file=upload.file
    )


def check_uploads(uploads: list[UploadFile]) -> list[CheckedUpload]:
    if len(uploads) > settings.max_files_per_upload:
        raise TooManyFilesError(settings.max_files_per_upload)
    return [check_upload(upload) for upload in uploads]
