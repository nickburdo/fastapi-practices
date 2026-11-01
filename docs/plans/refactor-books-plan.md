# План: рефакторинг модуля books по итогам код-ревью

**Статус:** выполнен (2026-11-01). Проверки этапа 9 пройдены (сервер — пользователем,
9.2–9.5 — на временной базе при код-ревью). Утверждён (2026-11-01), ревизии R1, R2, R3 утверждены (2026-11-01)
**Исполнитель реализации:** пользователь
**Версии:** FastAPI 0.162.0, Pydantic 2.14.2, pydantic-settings 2.16.2, SQLAlchemy 2.1.6, aiosqlite 0.22.1

## Цель

Исправить замечания код-ревью: структура модулей, зависимость нижних слоёв от FastAPI,
граница транзакции, контракт API (response_model, статус-код, путь, валидация),
вынос конфигурации, чистота кода.

## Вне рамок

- Эндпоинт `POST /setup-database` — логика не меняется (меняется только строка импорта `Base`, шаг 3.3).
- Пагинация `GET /books/` — отдельная задача.
- Миграции (Alembic), тесты.

## Журнал решений

| # | Вопрос | Решение | Кто |
|---|---|---|---|
| D1 | Кто вызывает `commit()` | Сервис. Репозиторий делает только `flush()` | пользователь |
| D2 | Пагинация | Не в этом плане | пользователь |
| D3 | Где `Base` и `Settings` | `shared/database/models.py`, `shared/config.py`; папка `models/` удаляется | пользователь |
| D4 | Формат плана | Файл в `docs/plans/` | пользователь |
| D5 | Пути к `.env` и `books.db` | Абсолютные, от корня проекта (`Path(__file__)`), т.к. pydantic-settings и SQLite считают относительные пути от текущего рабочего каталога | утверждено с планом |
| D6 | Ограничения длины | `title`, `author`: `min_length=1`, `max_length=255`; в ORM — `String(255)` для согласованности | утверждено с планом |
| D7 | Имя фабрики сессий | `async_session_maker` → `async_session_maker` | утверждено с планом |
| D8 | Имена модулей | Роль — в имени файла, сущность — в папке: `books/models.py`, `shared/database/models.py` (не `book-model.py` / `base.model.py` — дефис и точка в имени модуля Python недопустимы) | пользователь |

> D6: SQLite не проверяет длину `VARCHAR`, а существующая таблица без миграции не изменится.
> `String(255)` здесь — документация намерения и задел под другую СУБД; реальная проверка — в Pydantic.

## Журнал ревизий

| # | Дата | Изменение |
|---|---|---|
| R1 | 2026-11-01 | В каждый шаг добавлены явные строки импорта; фрагменты кода оформлены блоками кода. Шаги и решения не менялись. Добавлено D8 |
| R2 | 2026-11-01 | Исправлена проверка этапа 1: запуск через Python из `.venv`, из другой папки — с `PYTHONPATH`, добавлен ожидаемый вывод |
| R3 | 2026-11-01 | `shared/database/base.py` переименован в `shared/database/models.py` (импорт `from shared.database.models import Base`); обновлены D3, D8, структура, этапы 3–4 |

## Целевая структура

```
fastapi-as/
├── main.py
├── .env.example                # new
├── books/
│   ├── __init__.py
│   ├── models.py               # new  (from models/book.py: BookModel)
│   ├── schemas.py              # new  (from models/book.py: Pydantic schemas)
│   ├── repositories.py
│   ├── services.py
│   └── routes.py
├── shared/
│   ├── config.py               # new
│   └── database/
│       ├── __init__.py
│       ├── models.py           # new  (from models/base.py)
│       └── session.py
└── docs/plans/refactor-books-plan.md
```

Удаляется: `models/base.py`, `models/book.py`, папка `models/`.

> Переименование/перенос файлов в PyCharm: в диалоге Move/Rename снять галочки
> «Search in comments and strings» и «Search for text occurrences», иначе IDE правит и текст этого плана.

---

## Этап 1. Конфигурация (`shared/config.py`)

**1.1.** Создать `shared/config.py` с константой корня проекта.
`Path` — из стандартной библиотеки `pathlib`, **не** из `fastapi` (`fastapi.Path` — параметр пути URL).

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
```

**1.2.** В том же файле объявить класс `Settings`, унаследованный от `BaseSettings`
(без наследования `.env` и переменные окружения не читаются):

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

**1.3.** Добавить в `Settings` поле с URL базы по умолчанию
(тот же файл `books.db`, что сейчас, но по абсолютному пути):

```python
    database_url: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'books.db').as_posix()}"
```

**1.4.** В конце файла создать экземпляр:

```python
settings = Settings()
```

**1.5.** Создать `.env.example` в корне с закомментированной строкой-образцом.
Сам `.env` не создавать — без него работает значение по умолчанию.

```
# DATABASE_URL=sqlite+aiosqlite:///./books.db
```

**Проверка этапа** — обе команды печатают один и тот же абсолютный путь к `books.db`.
Используется Python из `.venv`: системный `python` в Git Bash может не иметь `pydantic-settings`.

Из корня проекта:

```
cd ~/PycharmProjects/fastapi-as
.venv/Scripts/python.exe -c "from shared.config import settings; print(settings.database_url)"
```

Из другой папки (например, `docs/`) — корень проекта передаётся через `PYTHONPATH`,
иначе Python не найдёт пакет `shared` (`ModuleNotFoundError`):

```
cd ~/PycharmProjects/fastapi-as/docs
PYTHONPATH=.. ../.venv/Scripts/python.exe -c "from shared.config import settings; print(settings.database_url)"
```

Ожидаемый вывод:

```
sqlite+aiosqlite:///C:/Users/nikbu/PycharmProjects/fastapi-as/books.db
```

## Этап 2. Сессия БД (`shared/database/session.py`)

**2.1.** Заменить строку подключения на значение из настроек:

```python
from shared.config import settings

engine = create_async_engine(settings.database_url)
```

**2.2.** Переименовать `async_session_maker` → `async_session_maker` (D7) и обновить использование в `get_session`:

```python
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
```

**2.3.** Добавить аннотацию возврата `get_session`:

```python
from collections.abc import AsyncIterator


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
```

`SessionDep` остаётся в этом файле — он нужен только роутам.

## Этап 3. Base (`shared/database/models.py`)

**3.1.** Создать `shared/database/models.py` (перенос из `models/base.py` без изменений):

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

**3.2.** Удалить `models/base.py`.

**3.3.** В `main.py` заменить строку импорта. Логику эндпоинта `/setup-database` не трогать.

```python
# was: from models.base import Base
from shared.database.models import Base
```

## Этап 4. ORM-модель (`books/models.py`)

**4.1.** Создать `books/models.py`, перенести туда `BookModel`. Импорты:

```python
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.models import Base
```

**4.2.** Колонки `title` и `author` — с длиной 255 (D6):

```python
from sqlalchemy import String

    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
```

## Этап 5. Pydantic-схемы (`books/schemas.py`)

**5.1.** Создать `books/schemas.py`, перенести `BookCreateSchema` и `BookSchema`. Импорт:

```python
from pydantic import BaseModel
```

**5.2.** В `BookCreateSchema` ограничить длину полей (D6):

```python
from pydantic import Field

    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
```

**5.3.** В `BookSchema` разрешить построение из ORM-объекта —
чтобы FastAPI мог провалидировать ORM-объект в схему ответа:

```python
from pydantic import ConfigDict

    model_config = ConfigDict(from_attributes=True)
```

Итоговая строка импорта файла после шагов 5.1–5.3:

```python
from pydantic import BaseModel, ConfigDict, Field
```

**5.4.** Удалить `models/book.py` и пустую папку `models/`.

> После этапов 4–5 приложение не запустится, пока не обновлены импорты в этапах 6–8.

## Этап 6. Репозиторий (`books/repositories.py`)

**6.1.** Импорт модели:

```python
from books.models import BookModel
```

**6.2.** Заменить тип параметра `session: SessionDep` → `session: AsyncSession` в обеих функциях;
убрать импорт `SessionDep`, добавить:

```python
from sqlalchemy.ext.asyncio import AsyncSession
```

**6.3.** `add_book`: заменить коммит на flush (D1).
`flush()` отправляет INSERT в рамках текущей транзакции и заполняет `id`.

```python
    # was: await session.commit()
    await session.flush()
```

**6.4.** Аннотации возврата:

```python
from collections.abc import Sequence


async def get_all_books(session: AsyncSession) -> Sequence[BookModel]:
    ...


async def add_book(new_book: BookModel, session: AsyncSession) -> BookModel:
    ...
```

**6.5.** Две пустые строки между функциями, перевод строки в конце файла.

## Этап 7. Сервис (`books/services.py`)

**7.1.** Импорты (убрать импорт `SessionDep`):

```python
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from books import repositories
from books.models import BookModel
from books.schemas import BookCreateSchema
```

**7.2.** Заменить тип параметра `session: SessionDep` → `session: AsyncSession` в обеих функциях.

**7.3.** `add_book`: создание модели одной строкой:

```python
    new_book = BookModel(**data.model_dump())
```

**7.4.** `add_book`: после вызова репозитория — коммит, затем вернуть книгу (D1).
Благодаря `expire_on_commit=False` атрибуты объекта остаются доступны после коммита.

```python
    book = await repositories.add_book(new_book=new_book, session=session)
    await session.commit()
    return book
```

**7.5.** Аннотации возврата:

```python
async def get_books(session: AsyncSession) -> Sequence[BookModel]:
    ...


async def add_book(data: BookCreateSchema, session: AsyncSession) -> BookModel:
    ...
```

**7.6.** Две пустые строки между функциями.

## Этап 8. Роуты (`books/routes.py`)

**8.1.** Удалить неиспользуемые импорты `select` и `BookModel`. Итоговые импорты файла
(с учётом шага 8.5):

```python
from fastapi import APIRouter, status

from books import services
from books.schemas import BookCreateSchema, BookSchema
from shared.database.session import SessionDep
```

**8.2.** Удалить закомментированный блок `read_book` (строки 18–24).

**8.3.** `GET /`: добавить схему ответа:

```python
@book_router.get("/", summary="List of books", response_model=list[BookSchema])
```

**8.4.** `POST`: путь `"/books"` → `"/"`.

**8.5.** `POST`: добавить схему ответа и статус 201:

```python
@book_router.post(
    "/",
    summary="Create a new book",
    response_model=BookSchema,
    status_code=status.HTTP_201_CREATED,
)
```

**8.6.** Две пустые строки между функциями.

## Этап 9. Проверка (вручную, через `/docs`)

**9.1.** Сервер стартует без ошибок импорта.

**9.2.** В `/docs` маршруты: `GET /books/`, `POST /books/`; пути `/books/books` нет.

**9.3.** `POST /books/` с валидными данными → `201`, тело `{id, title, author}`.

**9.4.** `POST /books/` с `title: ""` → `422`; с `title` длиной 256 символов → `422`.

**9.5.** `GET /books/` → `200`, созданная книга в списке; в схеме ответа в `/docs` видна `BookSchema`.

**9.6.** Перезапуск сервера → книга сохранилась (коммит действительно происходит в сервисе).

**9.7.** Запуск сервера из другой рабочей папки использует тот же `books.db` (проверка D5).

**9.8.** `POST /setup-database` по-прежнему работает (таблица `books` пересоздаётся — `BookModel`
регистрируется в `Base.metadata` через цепочку импортов `main → books.routes → books.services → books.models`).
