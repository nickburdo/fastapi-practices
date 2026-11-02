# План: пользователи в БД, регистрация, роуты пользователей, защита книг

**Статус:** выполнен 2026-11-02. Утверждён 2026-11-02 (третья редакция: токен в заголовке `Authorization` вместо
cookie; вторая — роуты пользователей и флаг `is_admin`), включая предложения A13–A25.
**Исполнитель реализации:** пользователь (код и git); Claude — план, код-ревью, проверки, отметка о выполнении
**Окружение:** FastAPI 0.162.0, SQLAlchemy 2.1.6, Alembic 1.20.1, authx 1.7.1, pwdlib 0.3.1 (новая), Ruff 0.17.3

## Журнал ревизий

| # | Дата | Изменение |
|---|---|---|
| R1 | 2026-11-02 | Этап 0 выполнен Claude по просьбе пользователя, в обратном порядке: сначала 0.3 (коммит плана `fb9c33c`), затем 0.2 (коммит кода из курса `c6008f1`). На результат порядок не влияет. Реализация начинается с этапа 1 |
| R2 | 2026-11-02 | Этап 15 (README) выполнен Claude по просьбе пользователя. После этапа 16 код-ревью нашло 4 расхождения с планом; Claude исправил их по просьбе пользователя (коммит `aab5297`): файл `users/schema.py` → `users/schemas.py`, `read_user` → `read_users`, в `users/dependencies.py` — `from fastapi import status` вместо `starlette.status` и текст 403 `"Admin rights required"` вместо `"User is not an admin"`. Код приведён к плану, сам план не менялся |

## Цель

Сейчас вход сделан по курсу: логин `test/test` зашит в `main.py`, секрет JWT лежит в коде, книги доступны всем.
После плана:

- в базе есть таблица `users` с флагом `is_admin`; миграция сразу создаёт админа `admin` с паролем `admin`;
- `POST /auth/register` создаёт пользователя и сразу выдаёт токен;
- `POST /auth/login` проверяет логин и пароль по базе и выдаёт токен;
- токен передаётся в заголовке `Authorization: Bearer <токен>` и живёт 30 минут;
- `GET /users/` — список пользователей, `GET /users/me` — текущий пользователь (для любого вошедшего);
- `DELETE /users/{user_id}` — удаление пользователя, только для админа;
- все роуты `/books/...` и `/users/...` без входа отвечают `401`. Токен удалённого пользователя тоже даёт `401`;
- тестовый `GET /protected` и старый `POST /login` удалены;
- секрет JWT хранится в `.env`.

## Вне рамок

- Выход (`logout`), смена пароля, `GET /users/{user_id}` — отдельные задачи.
- Refresh-токены: после истечения 30 минут нужно войти заново (A25). Следующий шаг — схема «короткий access-токен
  в памяти фронта + refresh-токен в cookie `httponly`».
- CORS (`CORSMiddleware`) — понадобится, когда появится фронтенд на другом домене.
- Назначение и снятие админа через API. Админ есть только из миграции.
- Одновременная регистрация двух одинаковых `username`: второй запрос получит `500` от уникального индекса,
  а не `409`. Для учебного проекта это допустимо.
- Тесты.

## Журнал решений

| # | Вопрос | Решение | Кто |
|---|---|---|---|
| A1 | Ветка | Продолжаем в `feature/auth-jwt`. Сначала отдельным коммитом фиксируется код из курса | пользователь |
| A2 | Как передаётся токен | Заголовок `Authorization: Bearer <токен>` (`JWT_TOKEN_LOCATION=["headers"]`), cookie не используется и не принимается. Причина: фронтенд может оказаться на другом сайте, а там cookie с `SameSite=lax` браузер не отправит; CSRF при заголовке не нужен. В Swagger работает кнопка **Authorize** (authx сам добавляет схему `AuthXBearer`), токен переживает F5 благодаря `persistAuthorization` | пользователь (изменено в третьей редакции, было «cookie без CSRF») |
| A3 | Как появляется админ | Миграция Alembic создаёт таблицу `users` и вставляет `admin` с готовым argon2-хэшем пароля `admin` и `is_admin=True` | пользователь |
| A4 | Права админа | Флаг `is_admin` (по умолчанию `False`). Админ отличается только одним: может удалять пользователей. Всё остальное доступно любому вошедшему | пользователь (изменено во второй редакции, было «ролей нет») |
| A5 | Ответы login и register | Оба возвращают только токен: `{"access_token": "...", "token_type": "bearer"}` (`TokenSchema`) — стандартная форма ответа OAuth2. Register отвечает `201` и сразу выдаёт токен (вход), занятый `username` → `409`. Данные пользователя — через `GET /users/me` | пользователь (изменено в третьей редакции, было «пользователь + cookie») |
| A6 | Валидация | `username` и `password` — не пустые (`min_length=1`). `username` не длиннее 50 символов (размер колонки) | пользователь (50 — предложение) |
| A7 | Где секрет JWT | Обязательное поле `jwt_secret_key` в `Settings`, значение в `.env`. Ключ не короче 32 символов (`Field(min_length=32)`), иначе приложение не запустится | пользователь (32 — предложение) |
| A8 | Адреса | `POST /auth/login`, `POST /auth/register` — роутер `auth_router` (`prefix="/auth"`, тег `Auth`). `/users/...` — роутер `users_router` (`prefix="/users"`, тег `Users`). Оба в `users/routes.py` | пользователь (общий файл — предложение) |
| A9 | Роуты пользователей | `GET /users/` — список, `GET /users/me` — текущий пользователь, `DELETE /users/{user_id}` — удаление | пользователь |
| A10 | Ответ пользователя | `{id, username, is_admin}` (`UserSchema`) — в списке и `/me`. Хэш пароля наружу не уходит | пользователь |
| A11 | Коды удаления | Не админ → `403 "Admin rights required"`; удалить себя → `400 "You cannot delete yourself"`; нет такого `user_id` → `404 "User not found"`; успех → `204` без тела. Порядок проверок: права → «не себя» → существует ли | пользователь (порядок — предложение) |
| A12 | Токен удалённого пользователя | Зависимость `get_current_user`: берёт id из токена и загружает пользователя из БД. Если его нет → `401 "User not found"`. Используется во всех защищённых роутах, включая книги. Один запрос к БД на каждый вызов | пользователь |
| A13 | Повторное использование id | `sqlite_autoincrement=True` у таблицы `users`. Проверено: без него SQLite отдаёт id удалённого последнего пользователя следующему, и старый токен удалённого пускает под новым (удалили `zed` с id 2 → `yan` получил id 2 → токен `zed` вернул `yan`). С `AUTOINCREMENT` id не повторяются | предложение — можно возразить |
| A14 | Токен с нечисловым `sub` | Токен из курсового `/login` подписан тем же механизмом, но в нём `sub="test"`, не число. `get_current_user` ловит `ValueError` и отвечает `401`, а не `500`. Проверено | предложение — можно возразить |
| A15 | Структура кода | Модуль `users/` со слоями как у `books/`: `models`, `schemas`, `exceptions`, `security`, `repositories`, `services`, `dependencies`, `routes`. Объект `auth` (AuthX) — в `shared/auth.py`, потому что его используют и `users`, и `books` | предложение — можно возразить |
| A16 | Хэширование паролей | `pwdlib[argon2]` — его рекомендует документация FastAPI (раздел OAuth2 with JWT) | предложение — можно возразить |
| A17 | Хранение токена на фронте | Забота фронта (память, `sessionStorage` или `localStorage`). Короткий срок жизни (A25) ограничивает ущерб, если токен украдут через XSS | пользователь (обсуждено) |
| A18 | Что лежит в токене | `uid=str(user.id)`: id не меняется, даже если когда-нибудь можно будет сменить `username` | предложение — можно возразить |
| A19 | Неверный логин или пароль | Один ответ на оба случая: `401 {"detail": "Invalid username or password"}`. Для несуществующего пользователя всё равно проверяется пароль (по `DUMMY_HASH`), чтобы время ответа не выдавало, есть такой `username` или нет. Так сделано в документации FastAPI | предложение — можно возразить |
| A20 | Схема входа | Одна схема `UserCredentialsSchema` для login и register | предложение — можно возразить |
| A21 | Как защищаются роуты | `dependencies=[Depends(get_current_user)]` на весь `book_router` и `users_router`. `/users/me` и удаление получают пользователя через `CurrentUserDep`/`CurrentAdminDep`; FastAPI кэширует зависимость в пределах запроса, поэтому пользователь грузится один раз | предложение — можно возразить |
| A22 | Создание токена | Одна функция `create_token(user) -> TokenSchema` в `users/routes.py` для login и register | предложение — можно возразить |
| A23 | Ошибки токена | Ответы authx (через `auth.handle_errors`): нет токена → `401 {"message": "Token Error", "error_type": "MissingTokenError"}`; испорченный токен → `422 {"message": "Invalid Token", "error_type": "JWTDecodeError"}` (так решила authx, проверено). Токен валиден, но пользователя нет → наш `401 {"detail": "User not found"}`. Оставляем как есть | предложение — можно возразить |
| A24 | Git | Коммит после каждого этапа, `merge --no-ff` в `main` после всего плана | по договорённости |
| A25 | Срок жизни токена | 30 минут (`JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30)`), как в примере документации FastAPI. Компромисс: токен в заголовке хранит фронт, и если его украдут, он проработает не дольше 30 минут; при этом в Swagger не нужно входить слишком часто. Refresh-токенов нет, поэтому после истечения — повторный вход | выбор Claude по просьбе пользователя |

> Проверено на копии проекта (2026-11-02): Ruff — без замечаний; `alembic upgrade head` создаёт `users`
> (`id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT`) и `admin` с `is_admin=1`; `alembic check` — схема совпадает
> с моделями; `downgrade -1` / `upgrade head` работают.
> Без заголовка: `/books/`, `/users/`, `/users/me`, `DELETE /users/2` → `401`; мусорный токен → `422`.
> `/protected`, `/login` → `404`.
> `admin/admin` → `200 {"access_token": ..., "token_type": "bearer"}`, cookie не ставится; в токене `sub="1"`,
> срок 30 минут. Неверный пароль, неизвестный пользователь → `401`.
> Регистрация: пустые поля → `422`; `bob` → `201` + токен; повтор → `409`.
> `bob`: `/users/me` → `{"id":2,"username":"bob","is_admin":false}`; `POST /books/` → `201`; `DELETE /users/1` → `403`.
> `admin`: `/users/` → `200`; удалить себя → `400`; `/users/999` → `404`; `/users/0` → `422`; удалить `bob` → `204`
> без тела. Токен удалённого `bob`: `/books/`, `/users/me` → `401`; повторная регистрация `bob` → новый id.
> Токен с `sub="test"` → `401`. Токен админа в cookie вместо заголовка → `401`.
> В OpenAPI схема `AuthXBearer`. Пустой или отсутствующий `JWT_SECRET_KEY` → ошибка запуска.

---

## Этап 0. Зафиксировать код из курса и план

> **Зачем.** Код из курса пока не закоммичен. Если зафиксировать его отдельным коммитом, в истории будет видно,
> с чего начали и что изменил этот план (A1).

**0.1.** Убедиться, что ты на ветке `feature/auth-jwt` и изменены только `main.py`, `pyproject.toml`, `uv.lock`
(плюс новый файл этого плана):

```
git branch --show-current
git status
```

**0.2.** Закоммитить код из курса:

```
git add main.py pyproject.toml uv.lock
git commit -m "Add authx cookie login from course"
```

**0.3.** Закоммитить план:

```
git add docs/plans/users-auth-plan.md
git commit -m "Add users auth plan"
```

## Этап 1. Зависимость `pwdlib`

> **Зачем.** Пароли нельзя хранить в базе открытым текстом, только хэш. `pwdlib` с алгоритмом Argon2 считает
> и проверяет такие хэши (A16).

**1.1.** **Остановить dev-сервер** (на Windows иначе `uv add` упадёт с `Access is denied`).

**1.2.** Добавить пакет:

```
uv add "pwdlib[argon2]"
```

Кавычки обязательны: без них оболочка может воспринять `[argon2]` как шаблон имени файла.

**1.3.** Коммит:

```
git add pyproject.toml uv.lock
git commit -m "Add pwdlib dependency"
```

## Этап 2. Секрет JWT в настройках (`shared/config.py`, `.env`)

> **Зачем.** Секрет, которым подписываются токены, не должен лежать в git: кто его знает, тот может выпустить
> себе токен любого пользователя. Переносим его в `.env`, который уже есть в `.gitignore` (A7).

**2.1.** `shared/config.py` — добавить импорт:

```python
from pydantic import Field
```

и поле в класс `Settings` (после `database_url`):

```python
    jwt_secret_key: str = Field(min_length=32)
```

Значения по умолчанию нет, поэтому без `.env` приложение и Alembic не запустятся и сразу скажут, чего не хватает.

**2.2.** Сгенерировать ключ:

```
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

**2.3.** Создать в корне проекта файл `.env` (в git он не попадёт) и вставить ключ из 2.2:

```
JWT_SECRET_KEY=сюда_ключ_из_2.2
```

**2.4.** `.env.example` — дописать в конец (сам ключ сюда **не** вставлять, файл попадает в git):

```
# Required. Secret key for signing JWT tokens, at least 32 characters.
# Generate one with: uv run python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=
```

**2.5.** Проверить, что настройки читаются (должно напечатать `64`):

```
uv run python -c "from shared.config import settings; print(len(settings.jwt_secret_key))"
```

**2.6.** Коммит (`.env` не добавлять):

```
git add shared/config.py .env.example
git commit -m "Add JWT secret key to settings"
```

## Этап 3. Настройка authx в отдельном модуле (`shared/auth.py`)

> **Зачем.** Объект `auth` нужен и модулю пользователей, и `main.py`. Если оставить его в `main.py`, модулям
> пришлось бы импортировать `main`, а `main` сам импортирует их, и получился бы циклический импорт.
> Отдельный модуль в `shared/` решает это (A15). Здесь же секрет берётся из настроек, токен переезжает
> из cookie в заголовок (A2), а срок жизни становится 30 минут (A25).

**3.1.** Создать файл `shared/auth.py`:

```python
from datetime import timedelta

from authx import AuthX, AuthXConfig

from shared.config import settings

auth_config = AuthXConfig(
    JWT_SECRET_KEY=settings.jwt_secret_key,
    JWT_TOKEN_LOCATION=["headers"],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),
)

auth = AuthX(config=auth_config)
```

Настройки cookie (`JWT_ACCESS_COOKIE_NAME`, `JWT_COOKIE_CSRF_PROTECT`) больше не нужны. Заголовок по умолчанию —
`Authorization`, тип — `Bearer`.

**3.2.** `main.py`:

- удалить импорты `from datetime import timedelta` и `from authx import AuthX, AuthXConfig`;
- добавить импорт `from shared.auth import auth`;
- удалить блок от `# Configure AuthX` до `auth = AuthX(config=config)` включительно;
- строку `auth.handle_errors(app)` **оставить**.

Старые `/login` и `/protected` пока остаются. Курсовой `/login` уже возвращает токен в теле ответа, так что
с заголовком он тоже работает. Cookie, которую он ставит, теперь просто игнорируется.

**3.3.** Проверить: `uv run ruff check`, запустить сервер, в `/docs` выполнить `POST /login` (`test`/`test`),
скопировать `access_token` из ответа в **Authorize**, затем `GET /protected` → `200`.

**3.4.** Коммит:

```
git add shared/auth.py main.py
git commit -m "Move authx setup to shared.auth"
```

## Этап 4. Модель пользователя (`users/models.py`)

> **Зачем.** Модель описывает таблицу `users`. `username` уникален, и это гарантирует сама база.
> В `hashed_password` хранится хэш, а не пароль. `is_admin` отличает админа (A4).
> `sqlite_autoincrement` не даёт SQLite выдать id удалённого пользователя новому (A13).

**4.1.** Создать пустой файл `users/__init__.py`.

**4.2.** Создать файл `users/models.py`:

```python
from sqlalchemy import String, false
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.models import Base


class UserModel(Base):
    __tablename__ = "users"
    # Never reuse ids of deleted users: a JWT stores the user id
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=false())
```

Что здесь происходит:

- `__table_args__` записан кортежем со словарём внутри, а не просто словарём. SQLAlchemy принимает оба варианта,
  но на словарь Ruff выдаёт `RUF012` (изменяемое значение атрибута класса);
- `default=False` — значение, которое подставит SQLAlchemy при создании `UserModel(...)` в коде;
- `server_default=false()` — значение по умолчанию в самой базе (`DEFAULT 0`), на случай вставки в обход ORM.

**4.3.** `migrations/env.py` — под строкой `import books.models ...` добавить:

```python
import users.models  # noqa: F401 (registers models in Base.metadata)
```

Без этого autogenerate не увидит новую модель (см. README, раздел «Миграции»).

**4.4.** Коммит:

```
git add users/__init__.py users/models.py migrations/env.py
git commit -m "Add UserModel"
```

## Этап 5. Миграция: таблица `users` и админ

> **Зачем.** Alembic создаст таблицу, а затем той же миграцией вставит админа (A3). Хэш пароля записан в миграции
> готовой строкой: миграция не зависит от кода приложения и через год выполнится так же, даже если
> `users/security.py` изменится.

**5.1.** Сгенерировать миграцию:

```
uv run alembic revision --autogenerate -m "create users table"
```

**5.2.** Открыть новый файл в `migrations/versions/` (имя `<ревизия>_create_users_table.py`; ревизия у тебя будет
своя). Проверить, что autogenerate создал `op.create_table("users", ...)` с четырьмя колонками (`is_admin`
с `server_default=sa.text("0")`), `PrimaryKeyConstraint("id")`, `UniqueConstraint("username")` и
`sqlite_autoincrement=True`, а `downgrade` делает `op.drop_table("users")`.

**5.3.** После строки `depends_on: ... = None` добавить константу:

```python
# Precomputed hash of the password "admin"; a literal keeps the migration
# independent of the hashing code in the application
ADMIN_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4"
    "$3WvTGb8jBiKlM6CGFC6lUA$LpmQNytPtMQb8rvMovZt1PpryVO78d/aDvz+opvJeuw"
)
```

Это хэш пароля `admin`, проверен через `pwdlib`. Если хочешь свой, сгенерируй его
(в каждом хэше своя случайная соль, поэтому строка будет другой, но тоже рабочей):

```
uv run python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('admin'))"
```

**5.4.** В `upgrade()` присвоить результат `op.create_table(...)` переменной: заменить `op.create_table(` на
`users_table = op.create_table(`. Затем после строки `# ### end Alembic commands ###` (внутри `upgrade`) добавить:

```python

    # Fixture admin user: username "admin", password "admin" (argon2 hash)
    op.bulk_insert(
        users_table,
        [
            {
                "username": "admin",
                "hashed_password": ADMIN_PASSWORD_HASH,
                "is_admin": True,
            }
        ],
    )
```

`op.create_table` возвращает объект таблицы, и `op.bulk_insert` вставляет в неё строки. `downgrade()` не меняется:
удаление таблицы удаляет и админа.

**5.5.** Применить и проверить:

```
uv run alembic upgrade head
uv run alembic check
```

`alembic check` должен ответить `No new upgrade operations detected.`

**5.6.** Коммит (подставь своё имя файла):

```
git add migrations/versions/<ревизия>_create_users_table.py
git commit -m "Add users table migration with admin fixture"
```

## Этап 6. Схемы (`users/schemas.py`)

> **Зачем.** `UserCredentialsSchema` — что клиент присылает при входе и регистрации (A6, A20). `UserSchema` —
> что мы отдаём о пользователе: `id`, `username`, `is_admin`, без хэша пароля (A10). `TokenSchema` — ответ
> login и register (A5).

**6.1.** Создать файл `users/schemas.py`:

```python
from pydantic import BaseModel, ConfigDict, Field


class UserCredentialsSchema(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class UserSchema(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

`token_type` по умолчанию `"bearer"`: роут передаёт только `access_token`.

**6.2.** Коммит:

```
git add users/schemas.py
git commit -m "Add user schemas"
```

## Этап 7. Исключения (`users/exceptions.py`)

> **Зачем.** Тот же подход, что с `BookNotFoundError`: сервис сообщает о проблеме своим исключением и ничего
> не знает про HTTP. Коды `409`, `401`, `404`, `400` выбирает роут или зависимость.

**7.1.** Создать файл `users/exceptions.py`:

```python
class UsernameTakenError(Exception):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username {username!r} is already taken")
        self.username = username


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} not found")
        self.user_id = user_id


class SelfDeletionError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} tried to delete themselves")
        self.user_id = user_id
```

У `InvalidCredentialsError` нет полей: ни в логах, ни в ответе не нужно уточнять, что именно было неверным (A19).

**7.2.** Коммит:

```
git add users/exceptions.py
git commit -m "Add user exceptions"
```

## Этап 8. Хэширование паролей (`users/security.py`)

> **Зачем.** Вся работа с `pwdlib` собрана в одном месте. Остальной код вызывает `hash_password` и
> `verify_password` и не зависит от того, каким алгоритмом считается хэш.

**8.1.** Создать файл `users/security.py`:

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

# Checked against when the user does not exist, so that the response time
# does not reveal whether a username is registered
DUMMY_HASH = password_hash.hash("dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)
```

`PasswordHash.recommended()` — это Argon2 с рекомендуемыми параметрами. `DUMMY_HASH` считается один раз
при импорте модуля (A19).

**8.2.** Коммит:

```
git add users/security.py
git commit -m "Add password hashing helpers"
```

## Этап 9. Репозиторий (`users/repositories.py`)

> **Зачем.** Как у книг, репозиторий только читает и пишет в базу. Для входа пользователя ищем по `username`
> (`select ... where`), для токена и удаления — по `id` (`session.get`).

**9.1.** Создать файл `users/repositories.py`:

```python
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import UserModel


async def get_all_users(session: AsyncSession) -> Sequence[UserModel]:
    query = select(UserModel).order_by(UserModel.id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_user_by_id(user_id: int, session: AsyncSession) -> UserModel | None:
    return await session.get(UserModel, user_id)


async def get_user_by_username(
    username: str, session: AsyncSession
) -> UserModel | None:
    query = select(UserModel).where(UserModel.username == username)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def add_user(new_user: UserModel, session: AsyncSession) -> UserModel:
    session.add(new_user)
    await session.flush()
    return new_user


async def delete_user(user: UserModel, session: AsyncSession) -> None:
    await session.delete(user)
    await session.flush()
```

Что здесь происходит:

- `scalar_one_or_none()` возвращает пользователя или `None`. Больше одного быть не может: `username` уникален;
- `session.delete` — в асинхронной сессии это корутина, поэтому с `await`. Как и в `add_user`, коммит
  делает сервис, а не репозиторий.

**9.2.** Коммит:

```
git add users/repositories.py
git commit -m "Add user repository functions"
```

## Этап 10. Сервис (`users/services.py`)

> **Зачем.** Здесь правила: «имя должно быть свободно», «пароль должен совпасть», «пользователь должен
> существовать», «нельзя удалить себя» (A11). Роуты этой логики не видят.

**10.1.** Создать файл `users/services.py`:

```python
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from users import repositories
from users.exceptions import (
    InvalidCredentialsError,
    SelfDeletionError,
    UsernameTakenError,
    UserNotFoundError,
)
from users.models import UserModel
from users.schemas import UserCredentialsSchema
from users.security import DUMMY_HASH, hash_password, verify_password


async def get_users(session: AsyncSession) -> Sequence[UserModel]:
    return await repositories.get_all_users(session=session)


async def get_user(user_id: int, session: AsyncSession) -> UserModel:
    user = await repositories.get_user_by_id(user_id=user_id, session=session)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


async def register_user(
    data: UserCredentialsSchema, session: AsyncSession
) -> UserModel:
    existing_user = await repositories.get_user_by_username(
        username=data.username, session=session
    )
    if existing_user is not None:
        raise UsernameTakenError(data.username)
    new_user = UserModel(
        username=data.username, hashed_password=hash_password(data.password)
    )
    user = await repositories.add_user(new_user=new_user, session=session)
    await session.commit()
    return user


async def authenticate_user(
    data: UserCredentialsSchema, session: AsyncSession
) -> UserModel:
    user = await repositories.get_user_by_username(
        username=data.username, session=session
    )
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise InvalidCredentialsError
    if not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsError
    return user


async def delete_user(
    user_id: int, current_user: UserModel, session: AsyncSession
) -> None:
    if user_id == current_user.id:
        raise SelfDeletionError(user_id)
    user = await get_user(user_id=user_id, session=session)
    await repositories.delete_user(user=user, session=session)
    await session.commit()
```

Что здесь происходит:

- `verify_password(..., DUMMY_HASH)` для несуществующего пользователя: результат не нужен, важно только,
  чтобы проверка заняла столько же времени, сколько для настоящего пользователя (A19);
- `delete_user` сначала проверяет «не себя», потом существование: удаление себя — `400`, даже если что-то
  ещё не так (A11). Проверку прав (`403`) делает зависимость до вызова сервиса (этап 11);
- `delete_user` использует `get_user`, поэтому «пользователь не найден» работает так же, как в `get_current_user`.

**10.2.** Коммит:

```
git add users/services.py
git commit -m "Add user services"
```

## Этап 11. Зависимости «текущий пользователь» и «текущий админ» (`users/dependencies.py`)

> **Зачем.** `auth.access_token_required` проверяет только подпись и срок токена. Пользователя из базы оно
> не загружает. Зависимость `get_current_user` загружает его по id из токена: если пользователя удалили,
> ответ `401` (A12). `get_current_admin` поверх неё проверяет флаг `is_admin` (`403`).

**11.1.** Создать файл `users/dependencies.py`:

```python
from typing import Annotated

from authx import TokenPayload
from fastapi import Depends, HTTPException, status

from shared.auth import auth
from shared.database.session import SessionDep
from users import services
from users.exceptions import UserNotFoundError
from users.models import UserModel


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(auth.access_token_required)],
    session: SessionDep,
) -> UserModel:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
    )
    try:
        user_id = int(payload.sub)
    except ValueError:
        # Token was signed by us but does not carry a numeric user id
        raise unauthorized from None
    try:
        return await services.get_user(user_id=user_id, session=session)
    except UserNotFoundError:
        raise unauthorized from None


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUserDep) -> UserModel:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin rights required"
        )
    return current_user


CurrentAdminDep = Annotated[UserModel, Depends(get_current_admin)]
```

Что здесь происходит:

- `Depends(auth.access_token_required)` — authx достаёт токен из заголовка `Authorization`, проверяет его
  и отдаёт содержимое (`TokenPayload`). Без токена или с испорченным токеном до нашего кода дело не доходит:
  authx сам ответит `401` или `422` (A23);
- `payload.sub` — строка, которую мы положили при входе (`uid=str(user.id)`, A18);
- `except ValueError` — на случай токена из курсового `/login`: там `sub="test"`, и `int("test")` упал бы
  с `500` (A14);
- `CurrentUserDep` / `CurrentAdminDep` — как `SessionDep`: короткая запись для параметров роутов.

**11.2.** Коммит:

```
git add users/dependencies.py
git commit -m "Add current user and admin dependencies"
```

## Этап 12. Роуты (`users/routes.py`)

> **Зачем.** Здесь два роутера. `auth_router` — вход и регистрация: то, что в курсе было одним роутом в `main.py`,
> теперь разложено по слоям. `users_router` — просмотр и удаление пользователей. Токен нужен и при входе,
> и при регистрации (A5), поэтому его создание вынесено в функцию `create_token` (A22).

**12.1.** Создать файл `users/routes.py`:

```python
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from shared.auth import auth
from shared.database.session import SessionDep
from users import services
from users.dependencies import CurrentAdminDep, CurrentUserDep, get_current_user
from users.exceptions import (
    InvalidCredentialsError,
    SelfDeletionError,
    UsernameTakenError,
    UserNotFoundError,
)
from users.models import UserModel
from users.schemas import TokenSchema, UserCredentialsSchema, UserSchema

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
users_router = APIRouter(
    prefix="/users", tags=["Users"], dependencies=[Depends(get_current_user)]
)


def create_token(user: UserModel) -> TokenSchema:
    return TokenSchema(access_token=auth.create_access_token(uid=str(user.id)))


@auth_router.post(
    "/register",
    summary="Register a new user and log in",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Username already taken"}},
)
async def register(data: UserCredentialsSchema, session: SessionDep) -> TokenSchema:
    try:
        user = await services.register_user(data=data, session=session)
    except UsernameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        ) from None
    return create_token(user=user)


@auth_router.post(
    "/login",
    summary="Log in",
    responses={401: {"description": "Invalid username or password"}},
)
async def login(data: UserCredentialsSchema, session: SessionDep) -> TokenSchema:
    try:
        user = await services.authenticate_user(data=data, session=session)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from None
    return create_token(user=user)


@users_router.get("/", summary="List of users", response_model=list[UserSchema])
async def read_users(session: SessionDep) -> Sequence[UserModel]:
    return await services.get_users(session=session)


@users_router.get("/me", summary="Current user", response_model=UserSchema)
async def read_current_user(current_user: CurrentUserDep) -> UserModel:
    return current_user


@users_router.delete(
    "/{user_id}",
    summary="Delete a user (admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "Admin cannot delete themselves"},
        403: {"description": "Admin rights required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: Annotated[int, Path(gt=0)],
    current_admin: CurrentAdminDep,
    session: SessionDep,
) -> None:
    try:
        await services.delete_user(
            user_id=user_id, current_user=current_admin, session=session
        )
    except SelfDeletionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        ) from None
```

Что здесь происходит:

- `uid=str(user.id)` — в токен попадает id пользователя (A18); authx требует строку;
- у `register` и `login` нет `response_model`: функции и так возвращают Pydantic-схему `TokenSchema`, FastAPI
  берёт модель ответа из аннотации `-> TokenSchema`. У `read_users` и `read_current_user` `response_model` нужен,
  потому что они возвращают модели SQLAlchemy;
- `dependencies=[Depends(get_current_user)]` у `users_router` — все роуты `/users/...` только для вошедших (A21);
- `CurrentAdminDep` в `delete_user` — сначала проверка прав (`403`), и только потом вызов сервиса (A11);
- `status_code=204` и `-> None` — FastAPI отдаст пустой ответ без тела;
- `from None` — как в `read_book`: ошибка ожидаемая, трассировка в логах не нужна.

**12.2.** Коммит:

```
git add users/routes.py
git commit -m "Add auth and users routes"
```

## Этап 13. Подключить роутеры, удалить старые `/login` и `/protected` (`main.py`)

> **Зачем.** Вход теперь живёт в `users/routes.py`. Код из курса в `main.py` (схема `UserLoginSchema`, проверка
> `test/test`, тестовый `/protected`) больше не нужен. В `main.py` остаётся только сборка приложения.

**13.1.** Итоговый `main.py` целиком:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from books.routes import book_router
from shared.auth import auth
from shared.database.session import engine
from users.routes import auth_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"persistAuthorization": True})

auth.handle_errors(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(book_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
```

Удалены: импорты `Depends`, `HTTPException`, `Response`, `BaseModel`; класс `UserLoginSchema`; роуты `login`
и `protected`. `auth.handle_errors(app)` остаётся: без него ошибки authx (нет токена, токен истёк) превращались бы
в `500` (A23).

**13.2.** Коммит:

```
git add main.py
git commit -m "Wire auth and users routers, remove course login"
```

## Этап 14. Защитить книги (`books/routes.py`)

> **Зачем.** Зависимость, указанная в `APIRouter(dependencies=[...])`, выполняется перед каждым роутом этого роутера.
> Одна строка защищает все три роута книг и все будущие (A21). Используем `get_current_user`, а не
> `auth.access_token_required`, чтобы удалённый пользователь не мог работать с книгами (A12).

**14.1.** Итоговые импорты файла:

```python
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from books import services
from books.exceptions import BookNotFoundError
from books.models import BookModel
from books.schemas import BookCreateSchema, BookSchema
from shared.database.session import SessionDep
from users.dependencies import get_current_user
```

**14.2.** Заменить создание роутера:

```python
book_router = APIRouter(
    prefix="/books",
    tags=["Books"],
    dependencies=[Depends(get_current_user)],
)
```

Сами роуты не меняются.

**14.3.** Коммит:

```
git add books/routes.py
git commit -m "Require login for books routes"
```

## Этап 15. README

> **Зачем.** Теперь `.env` обязателен, появились новые эндпоинты и админ. Без этого в README
> по разделу «Запуск» проект не запустится.

**15.1.** Раздел «Стек» — добавить строки в таблицу:

```
| Аутентификация | authx (JWT в заголовке `Authorization: Bearer`) |
| Хэширование паролей | pwdlib (Argon2) |
```

**15.2.** Раздел «Структура» — добавить строки:

```
users/               # модуль пользователей: models, schemas, security, repositories, services, dependencies, routes
shared/auth.py       # настройка authx (JWT в заголовке, 30 минут)
```

и заменить комментарий у `shared/config.py` на `# настройки (DATABASE_URL, JWT_SECRET_KEY)`.

**15.3.** Раздел «Запуск», пункт 2 — заменить целиком на:

````
2. Настройки. Скопируйте `.env.example` в `.env` и задайте `JWT_SECRET_KEY` (обязательно,
   не короче 32 символов):

   ```bash
   cp .env.example .env
   uv run python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Вставьте напечатанный ключ после `JWT_SECRET_KEY=`. Там же при желании можно задать
   `DATABASE_URL` (абсолютный путь); по умолчанию база — `books.db` в корне проекта.
````

**15.4.** Пункт 3 — после блока с командой дописать:

```
   Миграции создают админа: логин `admin`, пароль `admin`.
```

**15.5.** Таблицу эндпоинтов заменить на:

```
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

\* Нужен токен в заголовке `Authorization: Bearer <токен>`. Без него или если пользователь удалён — 401.
Токен живёт 30 минут, потом нужно войти заново. В `/docs`: выполнить `POST /auth/login`, скопировать
`access_token` из ответа и вставить в **Authorize** (токен сохраняется после перезагрузки страницы).
```

**15.6.** Коммит:

```
git add README.md
git commit -m "Document auth and users routes in README"
```

## Этап 16. Проверка (вручную, через `/docs`)

> Вход в Swagger: выполнить `POST /auth/login` или `POST /auth/register`, скопировать `access_token` из ответа,
> нажать **Authorize** и вставить токен (префикс `Bearer` не нужен). Чтобы сменить пользователя: **Authorize** →
> **Logout** → вставить другой токен. Токены `bob` и `admin` удобно держать в блокноте.

**16.1.** Ruff без замечаний и схема совпадает с моделями:

```
uv run ruff check
uv run ruff format --check
uv run alembic check
```

**16.2.** Перезапустить сервер, открыть `/docs`. Если в **Authorize** остался старый токен — **Logout**.

**16.3.** Без токена: `GET /books/`, `POST /books/`, `GET /users/`, `GET /users/me`, `DELETE /users/{user_id}` → `401`.
`GET /protected` и `POST /login` в `/docs` отсутствуют. Замок у роутов `/books` и `/users` есть, у `/auth` — нет.

**16.4.** `POST /auth/login` с `admin`/`wrong` → `401 {"detail": "Invalid username or password"}`;
с `nobody`/`x` → тот же ответ. `POST /auth/register` с пустым `username` → `422`.

**16.5.** `POST /auth/register` с `bob`/`p` → `201 {"access_token": "...", "token_type": "bearer"}`.
Сохранить токен `bob`, вставить в **Authorize**. `GET /users/me` → `{"id": ..., "username": "bob", "is_admin": false}`,
запомнить id. `GET /books/` → `200`; `POST /books/` → `201`.

**16.6.** Повторно `POST /auth/register` с `bob` или `admin` → `409 {"detail": "Username already taken"}`.

**16.7.** С токеном `bob`: `DELETE /users/1` → `403 {"detail": "Admin rights required"}`.

**16.8.** `POST /auth/login` с `admin`/`admin` → `200` + токен. Сохранить, сменить токен в **Authorize** на `admin`.
`GET /users/me` → `{"id": 1, "username": "admin", "is_admin": true}`; `GET /users/` → `admin` и `bob`.

**16.9.** С токеном `admin`: `DELETE /users/1` → `400 {"detail": "You cannot delete yourself"}`;
`DELETE /users/999` → `404`; `DELETE /users/{id bob}` → `204`.

**16.10.** Сменить токен на сохранённый токен удалённого `bob`: `GET /users/me` и `GET /books/` →
`401 {"detail": "User not found"}`. `POST /auth/login` с `bob`/`p` → `401`.

**16.11.** F5 на странице `/docs`: токен в **Authorize** сохранился (`persistAuthorization`).

Если после проверок что-то исправлялось — закоммитить исправление отдельным коммитом.

## Этап 17. Завершение

**17.1.** Отметить план выполненным — делает Claude, коммит:

```
git add docs/plans/users-auth-plan.md
git commit -m "Mark users auth plan as done"
```

**17.2.** Влить ветку в `main` и удалить её:

```
git switch main
git merge --no-ff feature/auth-jwt
git branch -d feature/auth-jwt
```
