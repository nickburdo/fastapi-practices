from pydantic import BaseModel, ConfigDict, Field


class BookCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)


class BookSchema(BookCreateSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)
