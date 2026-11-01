# План: миграции Alembic вместо `/setup-database`

**Статус:** утверждён (2026-11-01), включая предложения A6–A10
**Исполнитель реализации:** пользователь (код и команды); Claude — план, проверки, отметка о выполнении
**Окружение:** Python 3.15.1, uv 0.13.5, SQLAlchemy 2.1.6, aiosqlite 0.22.1, Alembic 1.20.1 (последняя), Ruff 0.17.3

## Цель

Закрыть пункты 1 и 6 код-ревью 2026-11-01:

- таблицы создаются и изменяются **миграциями Alembic**, а не эндпоинтом `/setup-database`,
  который удаляет все данные; эндпоинт удаляется;
- при остановке сервера закрываются соединения с базой (`engine.dispose()`).

## Вне рамок

- Новые поля/таблицы — только создание текущей таблицы `books` первой миграцией.
- Автоматическое применение миграций при старте сервера (A4).
- Публикация на GitHub.

## Журнал решений

| # | Вопрос | Решение | Кто |
|---|---|---|---|
| A1 | Чем создавать таблицы | Alembic, миграции | пользователь |
| A2 | Существующий `books.db` | Удалить; таблица создаётся первой миграцией пустой — старые данные не нужны | пользователь |
| A3 | Ruff и сгенерированные миграции | Alembic сам прогоняет `ruff check --fix` и `ruff format` по каждой новой миграции (post-write hooks) + разовая правка шаблона миграций | пользователь |
| A4 | Как применять миграции | Вручную: `alembic upgrade head`. Сервер схему базы не меняет | пользователь |
| A5 | Папка миграций | `migrations/` | пользователь |
| A6 | Шаблон Alembic | `pyproject_async`: async-движок (как в приложении), настройки Alembic — в `pyproject.toml`; `alembic.ini` — только логирование | предложение — можно возразить |
| A7 | Адрес базы для Alembic | Берётся из `settings.database_url` в `env.py` — тот же, что у приложения. Строка `sqlalchemy.url` в `alembic.ini` не используется | предложение — можно возразить |
| A8 | Пакетный режим SQLite | `render_as_batch=True` — иначе будущие изменения колонок в SQLite не сработают | предложение — можно возразить |
| A9 | Регистрация моделей | В `env.py` явный `import books.models  # noqa: F401` — без него Alembic «не видит» таблицу `books` | предложение — можно возразить |
| A10 | Git | Ветка `feat/alembic-migrations`, коммит после каждого этапа, слияние в `main` после всего плана (как в плане чистки) | предложение — можно возразить |

> Проверено на копии проекта (2026-11-01): `uv add alembic` → `alembic init -t pyproject_async migrations` →
> правки `env.py` → `revision --autogenerate` создаёт таблицу `books` с `VARCHAR(255)` →
> `upgrade head` / `downgrade base` / `upgrade head` работают; хуки Ruff дают чистый файл миграции;
> сервер без `/setup-database` работает (`POST` → `201`, `GET` → `200`), `engine.dispose()` вызывается при остановке.

---

## Этап 0. Ветка задачи

**0.1.** `main` чистый (кроме нового файла этого плана), создать ветку:

```
git switch main
git status
git switch -c feat/alembic-migrations
```

`git status` покажет `?? docs/plans/alembic-plan.md` — это нормально, файл переедет в ветку.

**0.2.** Закоммитить план:

```
git add docs/plans/alembic-plan.md
git commit -m "Add Alembic migrations plan"
```

## Этап 1. Установка Alembic

> **Что делаем.** Добавляем Alembic в зависимости проекта через uv — он запишется в `pyproject.toml` и `uv.lock`.
> Это зависимость приложения (не `dev`): без миграций базу не создать.

**1.1.** **Остановить сервер** (иначе на Windows возможен `Access is denied`). Затем:

```
uv add "alembic>=1.20.1"
```

**1.2.** Проверить:

```
alembic --version
```

Ожидаемо: `alembic 1.20.1`.

**1.3.** Коммит:

```
git add pyproject.toml uv.lock
git commit -m "Add Alembic dependency"
```

## Этап 2. Инициализация Alembic

> **Что делаем.** Одна команда создаёт «каркас» миграций по шаблону `pyproject_async` (A6):
>
> - `migrations/env.py` — скрипт, который Alembic запускает при каждой команде: как подключиться к базе и где модели;
> - `migrations/script.py.mako` — шаблон, по которому генерируются файлы миграций;
> - `migrations/versions/` — здесь будут лежать сами миграции;
> - `alembic.ini` — только настройки логирования;
> - раздел `[tool.alembic]` в конце `pyproject.toml` — где лежат миграции.

**2.1.** В корне проекта:

```
alembic init -t pyproject_async migrations
```

**2.2.** Проверить, что появилось:

```
git status
```

Ожидаемо: изменён `pyproject.toml`; новые `alembic.ini` и `migrations/`.

**2.3.** Коммит (файлы как их создал Alembic — свои правки будут видны отдельно в следующем коммите):

```
git add pyproject.toml alembic.ini migrations
git commit -m "Initialize Alembic with pyproject_async template"
```

## Этап 3. Подключение `env.py` к проекту

> **Проблема.** Сгенерированный `env.py` ничего не знает о проекте: адрес базы в нём — заглушка,
> а список таблиц (`target_metadata`) — `None`, поэтому автогенерация не увидит модель `BookModel`.
>
> **Что делаем.** Четыре правки в `migrations/env.py`.

**3.1.** Импорты — добавить после строки `from alembic import context`
(Ruff при сохранении расставит их по группам):

```python
import books.models  # noqa: F401  (registers models in Base.metadata)
from shared.config import settings
from shared.database.models import Base
```

`import books.models` нужен только ради побочного эффекта: при импорте класс `BookModel` регистрирует
таблицу `books` в `Base.metadata`. Комментарий `noqa: F401` говорит Ruff, что импорт «неиспользуемый» намеренно (A9).

**3.2.** Адрес базы — сразу после строки `config = context.config` (A7):

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
```

**3.3.** Список таблиц — заменить `target_metadata = None` на:

```python
target_metadata = Base.metadata
```

**3.4.** Пакетный режим SQLite (A8) — в **двух** местах.

В функции `run_migrations_offline` добавить параметр в вызов `context.configure(...)`:

```python
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
```

В функции `do_run_migrations` заменить вызов `context.configure(...)` на:

```python
    context.configure(
        connection=connection, target_metadata=target_metadata, render_as_batch=True
    )
```

**3.5.** Проверить, что Alembic подключается к базе и видит проект (команда только читает):

```
alembic current
```

Ожидаемо: строки `INFO ... Context impl SQLiteImpl.` и `Will assume non-transactional DDL.`, без ошибок.

## Этап 4. Ruff для новых миграций (A3)

> **Проблема.** Alembic генерирует файлы миграций в своём стиле: Ruff находит в каждом 6 замечаний
> (порядок импортов, устаревшая запись типов `Union[...]`).
>
> **Что делаем.** Правим шаблон миграций один раз и просим Alembic прогонять Ruff по каждой новой миграции.

**4.1.** В `migrations/script.py.mako` заменить строку импорта:

```
from typing import Sequence, Union
```

на:

```
from collections.abc import Sequence
```

**4.2.** Там же — три строки с `Union[...]`:

```
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}
```

**4.3.** В **конец** `pyproject.toml` добавить хуки:

```toml
[[tool.alembic.post_write_hooks]]
name = "ruff_fix"
type = "module"
module = "ruff"
options = "check --fix REVISION_SCRIPT_FILENAME"

[[tool.alembic.post_write_hooks]]
name = "ruff_format"
type = "module"
module = "ruff"
options = "format REVISION_SCRIPT_FILENAME"
```

`check --fix` не удаляет неиспользуемые импорты — это запрещено в настройках Ruff (`unfixable = ["F401"]`).

**4.4.** Коммит этапов 3–4:

```
git add migrations/env.py migrations/script.py.mako pyproject.toml
git commit -m "Configure Alembic env and Ruff hooks"
```

## Этап 5. Первая миграция и новая база

> **Что делаем.** Удаляем старую базу (A2), генерируем первую миграцию из модели, читаем её и применяем.

**5.1.** **Остановить сервер.** Удалить старую базу (в git её нет — она в `.gitignore`):

```
rm books.db
```

**5.2.** Сгенерировать миграцию:

```
alembic revision --autogenerate -m "create books table"
```

Ожидаемо в выводе:

```
INFO  [alembic.autogenerate.compare.tables] Detected added table 'books'
Generating ...\migrations\versions\<номер>_create_books_table.py ...  done
Running post write hook 'ruff_fix' ...
Running post write hook 'ruff_format' ...
```

`<номер>` — случайный идентификатор миграции, у вас будет свой.

**5.3.** **Прочитать** созданный файл `migrations/versions/<номер>_create_books_table.py`. Функции должны быть такими:

```python
def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("books")
    # ### end Alembic commands ###
```

Если в `upgrade()` что-то другое — остановиться, не применять.

**5.4.** Применить миграцию — создаётся новый `books.db` с таблицей `books`:

```
alembic upgrade head
```

**5.5.** Проверить состояние базы:

```
alembic current
```

Ожидаемо: `<номер> (head)`.

**5.6.** Коммит:

```
git add migrations/versions
git commit -m "Add initial migration: books table"
```

## Этап 6. `main.py`: убрать `/setup-database`, закрывать соединения

> **Что делаем.** Удаляем эндпоинт, который пересоздавал таблицы, и добавляем `lifespan` —
> функцию, которую FastAPI выполняет при запуске (до `yield`) и остановке (после `yield`) сервера.
> При остановке закрываем все соединения с базой.

**6.1.** Удалить эндпоинт `setup_database` целиком (декоратор `@app.post("/setup-database", ...)` и функцию)
и ставший ненужным импорт `from shared.database.models import Base`.

**6.2.** Добавить импорты:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
```

**6.3.** Перед `app = FastAPI()` добавить `lifespan` и передать его в приложение:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
```

**6.4.** Итоговый `main.py` целиком — для сверки:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from shared.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
```

**6.5.** Коммит:

```
git add main.py
git commit -m "Remove setup-database endpoint, dispose engine on shutdown"
```

## Этап 7. Проверка

**7.1.** Ruff без замечаний:

```
ruff check
ruff format --check
```

**7.2.** Сервер стартует; в `/docs` только `GET /books/` и `POST /books/` — `/setup-database` нет.

**7.3.** `GET /books/` → `200`, пустой список `[]`. `POST /books/` → `201`; `GET /books/` — книга в списке.

**7.4.** Остановка сервера — без ошибок в консоли.

**7.5.** Миграции откатываются и применяются заново (таблица пересоздаётся пустой — это ожидаемо):

```
alembic downgrade base
alembic upgrade head
alembic current
```

Ожидаемо: `Running downgrade ...`, затем `Running upgrade ...`, в конце `<номер> (head)`.

Если после проверок что-то исправлялось — закоммитить исправление отдельным коммитом.

## Этап 8. Шпаргалка: работа с миграциями

| Задача | Команда |
|---|---|
| Изменил модель — создать миграцию | `alembic revision --autogenerate -m "что изменилось"` → **прочитать файл** |
| Применить все новые миграции | `alembic upgrade head` |
| Откатить последнюю миграцию | `alembic downgrade -1` |
| Какая миграция применена к базе | `alembic current` |
| История миграций | `alembic history` |
| Собрать базу с нуля (новый компьютер, удалили `books.db`) | `alembic upgrade head` |

Правила:

- модель и её миграция — в **одном** коммите;
- автогенерация не понимает переименований: переименование колонки она запишет как «удалить + создать»
  (данные пропадут) — такие миграции править вручную (`op.alter_column(..., new_column_name=...)`);
- применённую и закоммиченную миграцию не редактировать — для исправления создать новую.

## Этап 9. Завершение

**9.1.** Отметить план выполненным — делает Claude. Коммит:

```
git add docs/plans/alembic-plan.md
git commit -m "Mark Alembic plan as done"
```

**9.2.** Влить ветку в `main` и удалить её:

```
git switch main
git merge --no-ff feat/alembic-migrations
git branch -d feat/alembic-migrations
```
