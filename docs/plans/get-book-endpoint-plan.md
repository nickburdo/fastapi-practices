# План: эндпоинт `GET /books/{book_id}`

**Статус:** утверждён (2026-11-01), включая предложения B4–B8
**Исполнитель реализации:** пользователь (код и git); Claude — план, проверки, отметка о выполнении
**Окружение:** FastAPI 0.162.0, SQLAlchemy 2.1.6, Ruff 0.17.3

## Цель

Получить одну книгу по её `id`: `GET /books/{book_id}` → `200` и книга; несуществующий `id` → `404`;
некорректный `id` (`0`, отрицательный, не число) → `422`. Заменяет закомментированный черновик в `books/routes.py`.

## Вне рамок

- Изменение и удаление книги (`PUT`/`PATCH`/`DELETE`) — отдельные задачи; исключение `BookNotFoundError`
  из этого плана им пригодится.
- Глобальный обработчик исключений (`app.exception_handler`) — пока одно место, где ловится исключение.
- Миграции — схема базы не меняется.

## Журнал решений

| # | Вопрос | Решение | Кто |
|---|---|---|---|
| B1 | Кто решает, что книги нет | Репозиторий возвращает `None`; сервис бросает своё исключение `BookNotFoundError` (обычный Python, без FastAPI); роут ловит его и отвечает `404` | пользователь |
| B2 | `book_id` ≤ 0 | `422` через `Path(gt=0)` — запрос до базы не доходит, ограничение видно в `/docs` | пользователь |
| B3 | Тело ответа 404 | `{"detail": "Book not found"}` — стандартный формат FastAPI | пользователь |
| B4 | Имена функций | Репозиторий: `get_book_by_id` (рядом с `get_all_books`); сервис: `get_book` (рядом с `get_books`) | предложение — можно возразить |
| B5 | Запрос к базе | `session.get(BookModel, book_id)` — поиск по первичному ключу; по документации SQLAlchemy возвращает `None`, если строки нет | предложение — можно возразить |
| B6 | 404 в документации API | `responses={404: {"description": "Book not found"}}` в декораторе — ответ 404 виден в `/docs` | предложение — можно возразить |
| B7 | Цепочка исключений | `raise HTTPException(...) from None` — «книги нет» это ожидаемый исход, а не сбой; в логах не нужна трассировка `BookNotFoundError` | предложение — можно возразить |
| B8 | Где исключение | Новый файл `books/exceptions.py`; исключение хранит `book_id` (для логов и будущих обработчиков); клиенту id не показывается (B3) | предложение — можно возразить |
| B9 | Git | Ветка `feat/get-book-by-id`, коммит после каждого этапа, слияние после всего плана | по договорённости |

> Проверено на копии проекта (2026-11-01): `/books/1` → `200`; `/books/999` → `404` `{"detail": "Book not found"}`;
> `/books/0`, `/books/-5` → `422` (`greater_than`); `/books/abc` → `422` (`int_parsing`); `GET /books/` по-прежнему `200`;
> в OpenAPI у `/books/{book_id}` ответы `200`, `404`, `422`, у параметра — `exclusiveMinimum: 0`;
> Ruff — без замечаний; `alembic check` — схема не изменилась.

---

## Этап 0. Ветка задачи

**0.1.** `main` чистый (кроме нового файла этого плана), создать ветку:

```
git switch main
git status
git switch -c feat/get-book-by-id
```

**0.2.** Закоммитить план:

```
git add docs/plans/get-book-endpoint-plan.md
git commit -m "Add GET /books/{book_id} plan"
```

## Этап 1. Исключение «книга не найдена» (`books/exceptions.py`)

> **Зачем.** Сервис должен сообщить «такой книги нет», не зная ничего про HTTP (так мы договорились при рефакторинге:
> FastAPI — только в роутах). Для этого — своё исключение. Как превратить его в ответ `404`, решает роут.

**1.1.** Создать файл `books/exceptions.py`:

```python
class BookNotFoundError(Exception):
    def __init__(self, book_id: int) -> None:
        super().__init__(f"Book {book_id} not found")
        self.book_id = book_id
```

**1.2.** Коммит:

```
git add books/exceptions.py
git commit -m "Add BookNotFoundError"
```

## Этап 2. Репозиторий (`books/repositories.py`)

> **Зачем.** Репозиторий только достаёт данные из базы. Нет строки — возвращает `None`, решений не принимает.

**2.1.** Добавить функцию в конец файла (импорты не меняются):

```python
async def get_book_by_id(book_id: int, session: AsyncSession) -> BookModel | None:
    return await session.get(BookModel, book_id)
```

**2.2.** Коммит:

```
git add books/repositories.py
git commit -m "Add get_book_by_id repository function"
```

## Этап 3. Сервис (`books/services.py`)

> **Зачем.** Здесь правило «если книги нет — это ошибка». Любой будущий код (изменение, удаление книги),
> который вызовет `get_book`, получит то же поведение.

**3.1.** Добавить импорт (Ruff при сохранении расставит по месту):

```python
from books.exceptions import BookNotFoundError
```

**3.2.** Добавить функцию в конец файла:

```python
async def get_book(book_id: int, session: AsyncSession) -> BookModel:
    book = await repositories.get_book_by_id(book_id=book_id, session=session)
    if book is None:
        raise BookNotFoundError(book_id)
    return book
```

**3.3.** Коммит:

```
git add books/services.py
git commit -m "Add get_book service"
```

## Этап 4. Эндпоинт (`books/routes.py`)

> **Зачем.** Роут — граница с HTTP: проверяет `book_id` (B2), вызывает сервис и превращает
> `BookNotFoundError` в ответ `404` (B1, B3).

**4.1.** Итоговые импорты файла:

```python
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from books import services
from books.exceptions import BookNotFoundError
from books.models import BookModel
from books.schemas import BookCreateSchema, BookSchema
from shared.database.session import SessionDep
```

**4.2.** Удалить закомментированный черновик `read_book` (блок, начинающийся с `# @app.get("/{book_id}"`)
и на его место — **между** `read_books` и `create_book` — вставить:

```python
@book_router.get(
    "/{book_id}",
    summary="Get a book by ID",
    response_model=BookSchema,
    responses={404: {"description": "Book not found"}},
)
async def read_book(
    book_id: Annotated[int, Path(gt=0)], session: SessionDep
) -> BookModel:
    try:
        return await services.get_book(book_id=book_id, session=session)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        ) from None
```

Что здесь происходит:

- `Annotated[int, Path(gt=0)]` — FastAPI сам проверяет, что `book_id` целое и больше 0, иначе `422`;
- `responses={404: ...}` — только для документации `/docs`, на поведение не влияет (B6);
- `from None` — не прикреплять исходное исключение к ответу (B7).

**4.3.** Коммит:

```
git add books/routes.py
git commit -m "Add GET /books/{book_id} endpoint"
```

## Этап 5. Проверка (вручную, через `/docs`)

**5.1.** Ruff без замечаний:

```
ruff check
ruff format --check
```

**5.2.** Создать книгу через `POST /books/`, запомнить её `id`.

**5.3.** `GET /books/{id}` с этим `id` → `200`, книга.

**5.4.** `GET /books/999` → `404`, тело `{"detail": "Book not found"}`.

**5.5.** `GET /books/0` → `422`. В `/docs` поле `book_id` не даст ввести `abc` — проверить можно в браузере:
`http://127.0.0.1:8000/books/abc` → `422`.

**5.6.** `GET /books/` по-прежнему работает.

**5.7.** В `/docs` у `GET /books/{book_id}` в разделе **Responses** — `200`, `404`, `422`.

Если после проверок что-то исправлялось — закоммитить исправление отдельным коммитом.

## Этап 6. Завершение

**6.1.** Отметить план выполненным — делает Claude, коммит:

```
git add docs/plans/get-book-endpoint-plan.md
git commit -m "Mark GET /books/{book_id} plan as done"
```

**6.2.** Влить ветку в `main` и удалить её:

```
git switch main
git merge --no-ff feat/get-book-by-id
git branch -d feat/get-book-by-id
```
