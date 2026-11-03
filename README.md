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
| Аутентификация | authx (JWT в заголовке `Authorization: Bearer`) |
| Хэширование паролей | pwdlib (Argon2) |
| Пакеты и окружение | uv |
| Линтер и форматтер | Ruff (dev-зависимость) |

## Структура

```
main.py              # приложение FastAPI, подключение роутеров
books/               # модуль книг: models, schemas, repositories, services, routes
files/               # модуль файлов: models, schemas, validation, storage, repositories, services, routes
users/               # модуль пользователей: models, schemas, security, repositories, services, dependencies, routes
shared/auth.py       # настройка authx (JWT в заголовке, 30 минут)
shared/config.py     # настройки (DATABASE_URL, JWT_SECRET_KEY, папка и лимиты загрузок)
shared/database/     # Base для моделей, движок и сессия
migrations/          # Alembic: env.py и versions/
docs/plans/          # планы реализации
```

## Запуск

1. Установить зависимости (создаст `.venv` по `uv.lock`):

   ```bash
   uv sync
   ```

2. Настройки. Скопируйте `.env.example` в `.env` и задайте `JWT_SECRET_KEY` (обязательно,
   не короче 32 символов):

   ```bash
   cp .env.example .env
   uv run python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Вставьте напечатанный ключ после `JWT_SECRET_KEY=`. Там же при желании можно задать
   `DATABASE_URL` (абсолютный путь); по умолчанию база — `books.db` в корне проекта.

3. Создать / обновить схему базы (сервер сам таблицы не создаёт):

   ```bash
   uv run alembic upgrade head
   ```

   Миграции создают админа: логин `admin`, пароль `admin`.

4. Запустить сервер разработки с автоперезагрузкой:

   ```bash
   uv run fastapi dev main.py
   ```

   или `uv run python main.py`.

API: http://127.0.0.1:8000, документация Swagger: http://127.0.0.1:8000/docs.

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация, возвращает токен (409, если имя занято) |
| POST | `/auth/login` | Вход, возвращает токен (401 при неверных данных) |
| GET | `/users/` | Список пользователей* |
| GET | `/users/me` | Текущий пользователь* |
| DELETE | `/users/{user_id}` | Удалить пользователя, только админ* (403 не админу, 400 при удалении себя, 404 если нет) |
| GET | `/books/` | Список книг* |
| GET | `/books/{book_id}` | Книга по ID (404, если нет)* |
| POST | `/books/` | Создать книгу* |
| POST | `/files/` | Загрузить 1–10 файлов* (400 / 413 / 415 при нарушении ограничений) |
| GET | `/files/` | Список своих файлов, админу — всех* |
| GET | `/files/{file_id}` | Скачать файл под исходным именем* (404, если нет или чужой) |
| DELETE | `/files/{file_id}` | Удалить файл: свой, админу — любой* (404, если нет или чужой) |

Загрузка файлов: до 10 файлов за запрос, до 10 МБ каждый (`MAX_FILES_PER_UPLOAD`, `MAX_UPLOAD_SIZE`).
Разрешены `.jpg .jpeg .png .webp .gif .pdf .txt .docx .xlsx`; Content-Type файла должен соответствовать
расширению. Файлы хранятся в `uploads/` (`UPLOAD_DIR`) под случайными именами.

\* Нужен токен в заголовке `Authorization: Bearer <токен>`. Без него или если пользователь удалён — 401.
Токен живёт 30 минут, потом нужно войти заново. В `/docs`: выполнить `POST /auth/login`, скопировать
`access_token` из ответа и вставить в **Authorize** (токен сохраняется после перезагрузки страницы).

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
