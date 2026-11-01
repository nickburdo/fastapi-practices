# fastapi-as

Учебный REST API для книг на FastAPI с асинхронной SQLAlchemy и SQLite.

## Стек

| Что | Чем |
|---|---|
| Язык | Python 3.15+ |
| Веб-фреймворк | FastAPI (`fastapi[standard]`, сервер — Uvicorn) |
| ORM | SQLAlchemy 2 (async) |
| База данных | SQLite через драйвер `aiosqlite` |
| Миграции | Alembic (async-шаблон `pyproject_async`) |
| Настройки | pydantic-settings (файл `.env`) |
| Пакеты и окружение | uv |
| Линтер и форматтер | Ruff (dev-зависимость) |

## Структура

```
main.py              # приложение FastAPI, подключение роутеров
books/               # модуль книг: models, schemas, repositories, services, routes
shared/config.py     # настройки (DATABASE_URL)
shared/database/     # Base для моделей, движок и сессия
migrations/          # Alembic: env.py и versions/
docs/plans/          # планы реализации
```

## Запуск

1. Установить зависимости (создаст `.venv` по `uv.lock`):

   ```bash
   uv sync
   ```

2. (Необязательно) Настройки. По умолчанию база — `books.db` в корне проекта.
   Чтобы указать другую, скопируйте `.env.example` в `.env` и задайте `DATABASE_URL`
   (абсолютный путь):

   ```bash
   cp .env.example .env
   ```

3. Создать / обновить схему базы (сервер сам таблицы не создаёт):

   ```bash
   uv run alembic upgrade head
   ```

4. Запустить сервер разработки с автоперезагрузкой:

   ```bash
   uv run fastapi dev main.py
   ```

   или `uv run python main.py`.

API: http://127.0.0.1:8000, документация Swagger: http://127.0.0.1:8000/docs.

| Метод | Путь | Описание |
|---|---|---|
| GET | `/books/` | Список книг |
| GET | `/books/{book_id}` | Книга по ID (404, если нет) |
| POST | `/books/` | Создать книгу |

> Зависимости добавляются только через uv: `uv add <пакет>` / `uv add --dev <пакет>`,
> не через `pip install`. На Windows перед `uv add` / `uv sync` остановите сервер —
> иначе будет `Access is denied` из-за заблокированных файлов в `.venv`.

## Миграции

Alembic берёт адрес базы из `settings.database_url` (тот же, что у приложения);
строка `sqlalchemy.url` в `alembic.ini` не используется. Настройки Alembic — в
разделе `[tool.alembic]` файла `pyproject.toml`, `alembic.ini` — только логирование.
Миграции применяются **вручную**.

### Применить все миграции

```bash
uv run alembic upgrade head
```

### Создать новую миграцию после изменения моделей

1. Измените модель (например, в `books/models.py`). Если добавили новый модуль
   с моделями — импортируйте его в `migrations/env.py` рядом с `import books.models`,
   иначе autogenerate его не увидит.
2. Сгенерируйте миграцию:

   ```bash
   uv run alembic revision --autogenerate -m "describe change"
   ```

   Файл появится в `migrations/versions/` и будет автоматически отформатирован Ruff.
3. **Проверьте сгенерированный файл** — autogenerate не всё определяет верно
   (например, переименования он видит как удаление + добавление).
4. Примените:

   ```bash
   uv run alembic upgrade head
   ```

5. Убедитесь, что модели и база совпадают:

   ```bash
   uv run alembic check
   ```

### Полезные команды

```bash
uv run alembic current      # текущая ревизия базы
uv run alembic history      # список миграций
uv run alembic downgrade -1 # откатить последнюю миграцию
uv run alembic downgrade base  # откатить всё
```

## Линтер и форматирование

```bash
uv run ruff check .
uv run ruff format .
```
