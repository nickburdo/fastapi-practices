import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi.concurrency import run_in_threadpool

from shared.config import settings


def make_stored_name(original_name: str) -> str:
    # Random name on disk; the extension is kept only for convenience
    return uuid.uuid4().hex + Path(original_name).suffix.lower()


def path_for(stored_name: str) -> Path:
    return settings.upload_dir / stored_name


def _write(source: BinaryIO, destination: Path) -> None:
    source.seek(0)
    with destination.open("wb") as target:
        shutil.copyfileobj(source, target)


async def save(source: BinaryIO, stored_name: str) -> None:
    await run_in_threadpool(_write, source, path_for(stored_name))


async def delete(stored_name: str) -> None:
    await run_in_threadpool(path_for(stored_name).unlink, missing_ok=True)


async def exists(stored_name: str) -> bool:
    return await run_in_threadpool(path_for(stored_name).is_file)
