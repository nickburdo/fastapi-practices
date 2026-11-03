# План: модуль файлов (`files/`) — загрузка, список, скачивание и удаление по id

**Статус:** утверждён 2026-11-03, в работе. Этап 0 — Claude, этапы 1–13 — пользователь.
**Исполнитель реализации:** пользователь (код и git); Claude — план, проверки, отметка о выполнении
**Окружение:** FastAPI 0.162.0, Starlette 1.10.0, SQLAlchemy 2.1.6, Ruff 0.17.3

## Журнал ревизий

| # | Дата | Изменение |
|---|---|---|
| — | — | — |

## Цель

Перевести учебный код загрузки файлов из `main.py` в отдельный модуль `files/` по образцу `books/`:

- `POST /files/` — загрузить 1–10 файлов за раз. Каждый получает случайное имя на диске, данные о нём
  пишутся в БД. Ответ `201` и список записей.
- `GET /files/` — список своих файлов (админ видит все).
- `GET /files/{file_id}` — скачать файл под исходным именем.
- `DELETE /files/{file_id}` — удалить файл (запись в БД и файл на диске); ответ `204`.

Старые роуты `POST /files`, `POST /multiple-files`, `GET /files/{filename}` удаляются.

## Вне рамок

- Проверка содержимого по первым байтам (magic bytes): тип проверяется по расширению и Content-Type (F5).
- Жёсткий лимит размера запроса. Starlette сохраняет весь запрос во временный файл ещё до вызова
  обработчика, поэтому наш лимит отклоняет большой файл, но не мешает его прислать. Настоящий
  потолок ставят на прокси (nginx `client_max_body_size`).
- Файлы, уже лежащие в `uploads/` от учебного кода: в БД их нет, через API они недоступны, их можно удалить
  вручную.
- Файлы удалённого пользователя: остаются как есть (F17), пункт записывается в бэклог.
- Тесты.

## Журнал решений

| # | Вопрос | Решение | Кто |
|---|---|---|---|
| F1 | Структура | Модуль `files/` по образцу `books/`: `models`, `schemas`, `exceptions`, `repositories`, `services`, `routes`, плюс `validation` (проверка загрузок) и `storage` (диск) | пользователь |
| F2 | Доступ | Только с токеном. У файла есть владелец (`owner_id`). Пользователь видит и скачивает только свои файлы, админ — все | пользователь |
| F3 | Типы | Картинки и документы: `.jpg .jpeg .png .webp .gif .pdf .txt .docx .xlsx` | пользователь |
| F4 | Лимиты | 10 МБ на файл, 10 файлов на запрос; оба значения в `Settings` (можно переопределить в `.env`) | пользователь |
| F5 | Проверка типа | Расширение должно быть в белом списке, и Content-Type от клиента должен совпадать с типом, закреплённым за этим расширением. Новых зависимостей нет. Следствие: клиент, который шлёт для `.docx` тип `application/octet-stream` (например, `curl` без `;type=`), получит `415` | пользователь |
| F6 | Несколько файлов | Один роут `POST /files/` со списком; если хоть один файл не прошёл проверку, отклоняется весь запрос | пользователь |
| F7 | Отдача | Всегда скачивание (`Content-Disposition: attachment`) под исходным именем | пользователь |
| F8 | Таблица `files` | `id` (int, как у книг), `owner_id` → `users.id` (с индексом), `original_name` (255), `stored_name` (64, уникальное), `content_type` (100), `size`, `created_at` (время сервера БД) | предложение P1, принято |
| F9 | Белый список | Расширение → единственный допустимый MIME-тип. SVG исключён: внутри него может быть JavaScript | предложение P2, принято |
| F10 | Порядок загрузки | Проверить все файлы → записать на диск → один коммит. Если что-то упало после начала записи, уже записанные файлы удаляются | предложение P3, принято |
| F11 | Коды ошибок | Неразрешённый тип → `415`; файл больше лимита → `413`; больше 10 файлов, пустой файл, имя длиннее 255 символов → `400`. В `detail` — имя проблемного файла | предложение P4, принято |
| F12 | Чужой файл | `404`, как будто файла нет (не раскрываем, что он существует). Запись в БД есть, а файла на диске нет — тоже `404` | предложение P5, принято |
| F13 | Блокирующий диск | Синхронная запись, удаление и проверка файла выполняются через `fastapi.concurrency.run_in_threadpool` внутри `files/storage.py`. Снаружи у `storage` асинхронные функции | предложение P6, принято; размещение в `storage` — предложение, можно возразить |
| F14 | Ответ API | `id`, `owner_id`, `original_name`, `content_type`, `size`, `created_at`. `stored_name` наружу не отдаётся | предложение P7, принято |
| F15 | Swagger | Обход `format: binary` для списка файлов переезжает в новый роут | предложение P9, принято |
| F16 | Git | Учебный код закоммитить в `files-work` и слить в `main`; работа — в ветке `feat/files-module` от свежего `main`; коммит после каждого этапа | пользователь |
| F17 | Удаление пользователя, у которого есть файлы | Оставить как есть, записать в бэклог (этап 12). Внешние ключи в SQLite не включены (`PRAGMA foreign_keys` нигде не задаётся), поэтому `DELETE /users/{id}` проходит, а записи его файлов остаются с несуществующим `owner_id`. Видит их только админ, и он может их удалить. id пользователей не переиспользуются (`sqlite_autoincrement`), так что чужие файлы новому пользователю не достанутся | пользователь |
| F18 | Сервис и FastAPI | `files/services.py` принимает `UploadFile` (тип FastAPI), в отличие от сервисов книг, где FastAPI не используется. Без этого пришлось бы заводить свой класс-обёртку для загрузки. Исключения сервиса остаются обычными Python-исключениями, коды HTTP выбирает роут | предложение — можно возразить |
| F19 | Отдельный `validation.py` | Проверка возвращает `CheckedUpload` (dataclass: очищенное имя, нормализованный тип, размер, файл). Сервис работает уже с проверенными данными и не повторяет очистку имени | предложение — можно возразить |
| F20 | Имя исключения «нет файла» | `StoredFileNotFoundError`, а не `FileNotFoundError`: так называется встроенное исключение Python | предложение — можно возразить |
| F21 | Путь роутов | `/files/` со слэшем на конце, как у `/books/` | предложение — можно возразить |
| F22 | Кто удаляет | Владелец и админ, то же правило, что для скачивания; чужой файл → `404`. Ответ — `204` без тела | пользователь |
| F23 | Порядок удаления | Сначала запись в БД (`delete` + `commit`), потом файл с диска. Если коммит упал, файл остаётся вместе со своей записью. Если не удалось удалить с диска, на диске остаётся лишний файл без записи — это безвредно. Если файла на диске уже нет, запись всё равно удаляется, ответ `204` | предложение — можно возразить |
| F24 | Общая проверка доступа | Проверка «есть ли запись и твоя ли она» вынесена в `_get_accessible_file`, её используют и `get_file`, и `delete_file`. Проверка наличия на диске — только в `get_file` (F12, F23) | предложение — можно возразить |

> Проверено на копии проекта (2026-11-03): Ruff — без замечаний; autogenerate создаёт таблицу `files`
> с FK, уникальным `stored_name` и индексом `ix_files_owner_id`; `alembic check` — схема совпадает.
> `bob` загружает `отчёт.TXT` (`text/plain; charset=utf-8`) и `..\..\a.docx` → `201`, имена `отчёт.TXT` и `a.docx`,
> на диске `<uuid>.txt`, `<uuid>.docx`. `.exe`, `.png` с `text/plain`, `.svg`, файл без расширения → `415`;
> пустой → `400`; имя из 300 символов → `400`; хороший файл + файл больше 10 МБ → `413`, на диск ничего не записано;
> 11 файлов → `400`; без файлов → `422`. Список: `bob` видит свои 2, `eve` — свой 1, `admin` — все 3.
> Скачивание: `attachment; filename*=utf-8''%D0%BE...`, содержимое совпадает; `eve` → файл `bob` → `404`;
> `admin` → чужой файл → `200`; `/files/999` → `404`; `/files/0` → `422`; запись есть, файла на диске нет → `404`.
> Сбой БД после записи файлов → `500`, записанные файлы удалены. Без токена → `401`. `/multiple-files` → `404`.
> В Swagger у поля загрузки `items: {type: string, format: binary}`, то есть кнопки выбора файлов.
> Удаление: без токена → `401`; чужой файл → `404`, файл остаётся; свой → `204` без тела, затем `GET` → `404`,
> файл с диска удалён; повторное удаление → `404`; админ удаляет чужой → `204`; записи без файла на диске → `204`,
> запись удалена; `/files/999` → `404`; `/files/0` → `422`. В OpenAPI у `DELETE` ответы `204`, `404`, `422`.
> `created_at` заполняется сразу после INSERT без дополнительного запроса: SQLAlchemy 2.x по умолчанию
> (`eager_defaults="auto"`) получает его через `RETURNING`.

---

## Этап 0. Зафиксировать учебный код, ветка, план

**Проблема.** В `files-work` лежат незакоммиченные правки из курса (`main.py`, `.gitignore`). Этот план их
переписывает, а по правилу проекта каждая задача ведётся в своей ветке от свежего `main`.

**Что делаем.** Коммитим учебный код и сливаем его в `main`, чтобы он остался в истории. Затем создаём новую ветку
и коммитим план.

**0.1.** Закоммитить учебный код (файл этого плана пока не добавлять):

```
git status
git add main.py .gitignore
git commit -m "Add file upload endpoints from course"
```

**0.2.** Слить в `main` и создать ветку задачи:

```
git switch main
git merge --no-ff files-work
git switch -c feat/files-module
```

**0.3.** Закоммитить план:

```
git add docs/plans/files-module-plan.md
git commit -m "Add files module plan"
```

---

## Этап 1. Настройки (`shared/config.py`)

**Проблема.** Папка загрузок зашита в `main.py` (`UPLOAD_DIR`), лимитов нет.

**Что делаем.** Добавляем в `Settings` папку и оба лимита (F4). `gt=0` не даст задать в `.env` ноль или отрицательное
число: приложение упадёт при запуске с понятной ошибкой.

**1.1.** В `class Settings` после строки `jwt_secret_key: ...` добавить:

```python
    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_size: int = Field(default=10 * 1024 * 1024, gt=0)  # bytes, per file
    max_files_per_upload: int = Field(default=10, gt=0)
```

`Path` и `Field` в файле уже импортированы.

**1.2.** Коммит:

```
git add shared/config.py
git commit -m "Add upload settings"
```

---

## Этап 2. Модель (`files/models.py`)

**Проблема.** Данные о файлах негде хранить.

**Что делаем.** Создаём пакет `files` и модель (F8). `stored_name` уникален: это имя файла на диске.
`created_at` заполняет сама БД (`server_default=func.now()`, в SQLite — `CURRENT_TIMESTAMP`, время в UTC).

**2.1.** Создать пустой файл `files/__init__.py`.

**2.2.** Создать `files/models.py`:

```python
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.models import Base


class FileModel(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

**2.3.** Коммит:

```
git add files/__init__.py files/models.py
git commit -m "Add file model"
```

---

## Этап 3. Миграция: таблица `files`

**Проблема.** Таблицы в базе нет, а Alembic не знает о новой модели.

**Что делаем.** Регистрируем модель в `migrations/env.py`, генерируем миграцию и применяем её вручную.

**3.1.** В `migrations/env.py` между `import books.models ...` и `import users.models ...` добавить:

```python
import files.models  # noqa: F401 (registers models in Base.metadata)
```

**3.2.** Сгенерировать миграцию:

```
uv run alembic revision --autogenerate -m "create files table"
```

**3.3.** Открыть новый файл `migrations/versions/<ревизия>_create_files_table.py` (ревизия у тебя будет своя).
Проверить, что `upgrade` содержит `op.create_table("files", ...)` с семью колонками (у `created_at` —
`server_default=sa.text("(CURRENT_TIMESTAMP)")`), `ForeignKeyConstraint(["owner_id"], ["users.id"])`,
`PrimaryKeyConstraint("id")`, `UniqueConstraint("stored_name")`, а затем `create_index(... "ix_files_owner_id" ...)`.
`downgrade` удаляет индекс и таблицу. Править ничего не нужно.

**3.4.** Применить и сверить:

```
uv run alembic upgrade head
uv run alembic check
```

`alembic check` должен ответить `No new upgrade operations detected.`

**3.5.** Коммит (подставь своё имя файла):

```
git add migrations/env.py migrations/versions/<ревизия>_create_files_table.py
git commit -m "Add files table migration"
```

---

## Этап 4. Схема ответа (`files/schemas.py`)

**Проблема.** Нужен формат, в котором API отдаёт данные о файле, без внутреннего `stored_name` (F14).

**Что делаем.** Одна схема для ответа. Схема входных данных не нужна: на входе файлы, а не JSON.

**4.1.** Создать `files/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileSchema(BaseModel):
    id: int
    owner_id: int
    original_name: str
    content_type: str
    size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**4.2.** Коммит:

```
git add files/schemas.py
git commit -m "Add file schema"
```

---

## Этап 5. Исключения (`files/exceptions.py`)

**Проблема.** Сервису нужно сообщать о проблемах с загрузкой и об отсутствии файла, не зная про HTTP
(тот же подход, что и у книг).

**Что делаем.** Общий базовый класс `UploadValidationError` для всех причин отклонить загрузку: роут сначала
ловит подклассы со своими кодами (`415`, `413`), а всё остальное через базовый класс превращает в `400` (F11).
Сообщение формируется в исключении, роут отдаёт его в `detail` через `str(exc)`.

**5.1.** Создать `files/exceptions.py`:

```python
class UploadValidationError(Exception):
    """The upload request is rejected as a whole."""


class TooManyFilesError(UploadValidationError):
    def __init__(self, max_count: int) -> None:
        super().__init__(f"Too many files: at most {max_count} per request")
        self.max_count = max_count


class FileNameTooLongError(UploadValidationError):
    def __init__(self, max_length: int) -> None:
        super().__init__(f"File name is longer than {max_length} characters")
        self.max_length = max_length


class UnsupportedFileTypeError(UploadValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"File '{filename}' has an unsupported type")
        self.filename = filename


class EmptyFileError(UploadValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"File '{filename}' is empty")
        self.filename = filename


class FileTooLargeError(UploadValidationError):
    def __init__(self, filename: str, max_size: int) -> None:
        super().__init__(f"File '{filename}' is larger than {max_size} bytes")
        self.filename = filename
        self.max_size = max_size


class StoredFileNotFoundError(Exception):
    def __init__(self, file_id: int) -> None:
        super().__init__(f"File {file_id} not found")
        self.file_id = file_id
```

В `FileNameTooLongError` имени файла нет намеренно: оно длиннее 255 символов и раздуло бы ответ.

**5.2.** Коммит:

```
git add files/exceptions.py
git commit -m "Add file exceptions"
```

---

## Этап 6. Проверка загрузок (`files/validation.py`)

**Проблема.** Все проверки (количество, имя, тип, размер) нужно выполнить до записи на диск, причём для всех
файлов сразу (F6, F10).

**Что делаем.**

- `check_upload` проверяет один файл и возвращает `CheckedUpload` с уже очищенными данными (F19).
- Имя: `Path(...).name` отрезает папки (`..\..\a.docx` → `a.docx`).
- Тип: параметры отрезаются (`text/plain; charset=utf-8` → `text/plain`), затем тип сравнивается с закреплённым
  за расширением. Расширение без учёта регистра, так что `.JPG` подходит. Файл без расширения или с неизвестным
  расширением даёт `None`, а `None` ни с каким типом не совпадёт, то есть такой файл тоже получит `415`.
- Размер: `UploadFile.size` Starlette заполняет при разборе запроса, читать файл для этого не нужно.
- `check_uploads` сначала проверяет количество, потом каждый файл. Первая же ошибка прерывает проверку.

**6.1.** Создать `files/validation.py`:

```python
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
```

**6.2.** Коммит:

```
git add files/validation.py
git commit -m "Add upload validation"
```

---

## Этап 7. Хранилище на диске (`files/storage.py`)

**Проблема.** Работа с диском блокирующая (предупреждение Ruff про `open` в `async def`), и она не должна
расползаться по сервису.

**Что делаем.** Всё, что касается диска, собираем в одном месте (F13):

- `make_stored_name` создаёт случайное имя: `uuid4().hex` + расширение в нижнем регистре. Имя от клиента
  на диск больше не попадает, поэтому одноимённые файлы не перезаписывают друг друга, а выйти за пределы папки нельзя.
- `path_for` превращает имя на диске в полный путь.
- Синхронную работу (`_write`, `unlink`, `is_file`) выполняем в пуле потоков через `run_in_threadpool`, поэтому
  event loop не блокируется.
- `shutil.copyfileobj` копирует файл кусками, а не читает его целиком в память.
- `source.seek(0)` нужен для надёжности: если файл кто-то уже читал, копирование начнётся с начала.

**7.1.** Создать `files/storage.py`:

```python
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
```

**7.2.** Коммит:

```
git add files/storage.py
git commit -m "Add file storage"
```

---

## Этап 8. Репозиторий (`files/repositories.py`)

**Проблема.** Нужны запросы к таблице `files`.

**Что делаем.** Четыре функции, как у книг:

- `get_files` получает `owner_id`. Значение `None` означает «все файлы» (для админа), число — фильтр по
  владельцу. Какое значение передать, решает сервис.
- `get_file_by_id` возвращает `None`, если записи нет.
- `add_files` добавляет записи и делает `flush`, но не коммит: коммит делает сервис.
- `delete_file` удаляет уже найденную запись (`session.delete` в async — с `await`) и тоже без коммита.

**8.1.** Создать `files/repositories.py`:

```python
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
```

**8.2.** Коммит:

```
git add files/repositories.py
git commit -m "Add file repository"
```

---

## Этап 9. Сервис (`files/services.py`)

**Проблема.** Нужно связать проверку, диск и БД и реализовать правила доступа (F2, F12).

**Что делаем.**

- `get_files`: админу передаём `owner_id=None` (все файлы), остальным — их собственный `id`.
- `_get_accessible_file` (F24): «записи нет» и «чужой файл» дают одно и то же исключение, и клиент не может
  отличить эти случаи (F12). Подчёркивание в начале имени означает, что функция внутренняя и роуты её не вызывают.
- `get_file`: вдобавок к общей проверке — «записи есть, файла на диске нет» → то же исключение.
- `delete_file`: сначала запись в БД и `commit`, потом файл с диска (F23). Наличие файла на диске не проверяется:
  запись без файла тоже нужно уметь удалить.
- `upload_files`:
  1. Сначала `check_uploads` для всех файлов: при ошибке ничего не записано.
  2. Имя на диске добавляется в `stored_names` **до** записи. Если запись оборвётся на середине, недописанный файл
     тоже удалится.
  3. Один `commit` на всю пачку.
  4. При любой ошибке после начала записи удаляем всё записанное и пробрасываем исключение дальше (F10).
     Если упал `commit`, сессию откатит `get_session`.

**9.1.** Создать `files/services.py`:

```python
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
```

**9.2.** Коммит:

```
git add files/services.py
git commit -m "Add file service"
```

---

## Этап 10. Роуты (`files/routes.py`)

**Проблема.** Нужны четыре эндпоинта, которые переводят исключения сервиса в коды HTTP.

**Что делаем.**

- `CurrentUserDep` в параметрах каждого роута: пользователь нужен самому роуту, а не только для проверки токена,
  поэтому `dependencies=[...]` на роутере, как у книг, здесь не подходит. Замок в Swagger всё равно появится.
- `POST`: порядок `except` важен. Подклассы (`415`, `413`) идут перед базовым `UploadValidationError` (`400`),
  иначе базовый класс перехватит всё. `responses=` показывает эти коды в `/docs`.
- `GET /{file_id}`: `Path(gt=0)`, как у книг. `FileResponse(..., filename=...)` сам ставит
  `Content-Disposition: attachment`, а для имён не латиницей — `filename*=utf-8''...` (F7).
  `response_class=FileResponse` говорит документации, что ответ — файл, а не JSON.
- `DELETE /{file_id}`: `status_code=204` и возвращаемый тип `None`, тела у ответа нет (F22).

**10.1.** Создать `files/routes.py`:

```python
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
```

`HTTP_413_CONTENT_TOO_LARGE` — актуальное имя константы. Старое `HTTP_413_REQUEST_ENTITY_TOO_LARGE` тоже есть,
но оно устаревшее.

**10.2.** Коммит:

```
git add files/routes.py
git commit -m "Add file routes"
```

---

## Этап 11. `main.py`: убрать учебные роуты, подключить роутер

**Проблема.** В `main.py` остались учебные роуты и `UPLOAD_DIR`, которые теперь заменены модулем.

**Что делаем.** Удаляем три роута и `UPLOAD_DIR`. `lifespan` создаёт папку из настроек. Подключаем `files_router`.

**11.1.** Привести `main.py` к виду:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from files.routes import files_router
from shared.auth import auth
from shared.config import settings
from shared.database.session import engine
from users.routes import auth_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)  # Register error handlers for proper responses


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(book_router)
app.include_router(files_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
```

Ушли импорты `Path`, `Annotated`, `File`, `HTTPException`, `UploadFile`, `FileResponse`: они больше не нужны.

**11.2.** Проверка и коммит:

```
uv run ruff check
uv run ruff format --check
git add main.py
git commit -m "Move file endpoints from main to files module"
```

---

## Этап 12. README, `.env.example`, бэклог

**Проблема.** В документации нет нового модуля, роутов и настроек; решение F17 нигде не записано.

**Что делаем.** Дописываем структуру, таблицу роутов, необязательные переменные и пункт бэклога.

**12.1.** `README.md`, раздел «Структура»: после строки `books/ ...` добавить:

```
files/               # модуль файлов: models, schemas, validation, storage, repositories, services, routes
```

и заменить строку `shared/config.py` на:

```
shared/config.py     # настройки (DATABASE_URL, JWT_SECRET_KEY, папка и лимиты загрузок)
```

**12.2.** `README.md`, таблица роутов: после строки `POST | /books/` добавить:

```
| POST | `/files/` | Загрузить 1–10 файлов* (400 / 413 / 415 при нарушении ограничений) |
| GET | `/files/` | Список своих файлов, админу — всех* |
| GET | `/files/{file_id}` | Скачать файл под исходным именем* (404, если нет или чужой) |
| DELETE | `/files/{file_id}` | Удалить файл: свой, админу — любой* (404, если нет или чужой) |
```

и сразу под таблицей, перед строкой со сноской `\*`, добавить абзац:

```
Загрузка файлов: до 10 файлов за запрос, до 10 МБ каждый (`MAX_FILES_PER_UPLOAD`, `MAX_UPLOAD_SIZE`).
Разрешены `.jpg .jpeg .png .webp .gif .pdf .txt .docx .xlsx`; Content-Type файла должен соответствовать
расширению. Файлы хранятся в `uploads/` (`UPLOAD_DIR`) под случайными именами.
```

**12.3.** `.env.example`: в конец файла добавить:

```
# Optional. Folder for uploaded files (default: uploads/ in the project root), absolute path.
# UPLOAD_DIR=C:/absolute/path/to/uploads
# Optional. Upload limits: max size of one file in bytes (default 10 MB) and max files per request (default 10).
# MAX_UPLOAD_SIZE=10485760
# MAX_FILES_PER_UPLOAD=10
```

**12.4.** `docs/backlog.md`: в конец файла добавить раздел (F17):

```
## Файлы

Источник: план `docs/plans/files-module-plan.md` (решение F17), 2026-11-03.

| # | Проблема | Где | Чем грозит | Возможное решение |
|---|---|---|---|---|
| B6 | При удалении пользователя его файлы остаются: внешние ключи в SQLite не включены, `files.owner_id` указывает на удалённого пользователя | `users/services.py` → удаление пользователя; `files/models.py` | Записи и файлы на диске копятся; видит и может удалить их только админ. Новому пользователю они не достанутся: id не переиспользуются (`sqlite_autoincrement`) | Удалять файлы пользователя (записи и диск) в сервисе удаления пользователя; или включить `PRAGMA foreign_keys=ON` + `ondelete="CASCADE"` и отдельно чистить диск |
```

**12.5.** Коммит:

```
git add README.md .env.example docs/backlog.md
git commit -m "Document files module"
```

---

## Этап 13. Проверка (вручную, через `/docs`)

**13.1.** Без ошибок должны пройти:

```
uv run ruff check
uv run ruff format --check
uv run alembic check
```

**13.2.** Перезапустить сервер, открыть `/docs`. Войти как `admin` (`POST /auth/login`, токен — в **Authorize**).
Зарегистрировать второго пользователя (`POST /auth/register`), его токен сохранить отдельно.

**13.3.** Без токена (**Logout**): все четыре роута `/files` → `401`.

**13.4.** Под вторым пользователем `POST /files/` (кнопки **Choose File**, **Add string item** для второго файла):

- `.txt` + `.png` → `201`, в ответе два объекта без `stored_name`; в `uploads/` два файла с именами вида `<32 символа>.txt`;
- `.exe` или `.svg` → `415`;
- пустой `.txt` → `400`;
- 11 файлов → `400`;
- файл больше 10 МБ вместе с нормальным → `413`, в `uploads/` ничего нового не появилось.

**13.5.** `GET /files/` под вторым пользователем — только его файлы; под `admin` — все.

**13.6.** `GET /files/{file_id}`: свой файл → `200`, в Swagger появляется ссылка **Download file** с исходным именем;
под `admin` — файл другого пользователя → `200`. Под вторым пользователем — файл `admin` (сначала загрузить его
под `admin`) → `404`. `/files/999` → `404`; `/files/0` → `422`.

**13.7.** `DELETE /files/{file_id}`: под вторым пользователем — файл `admin` → `404`, файл на месте; свой файл → `204`,
затем `GET` этого id → `404`, из `uploads/` файл исчез; повторное удаление → `404`. Под `admin` — файл второго
пользователя → `204`.

**13.8.** `POST /multiple-files` и `GET /files/<имя>` в `/docs` отсутствуют.

---

## Этап 14. Завершение

**14.1.** Код-ревью ветки (Claude), правки по его итогам — отдельными коммитами.

**14.2.** Слияние:

```
git switch main
git merge --no-ff feat/files-module
```

**14.3.** Claude отмечает план выполненным (строка «Статус») и записывает отклонения в журнал ревизий.
