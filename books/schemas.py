from pydantic import BaseModel, ConfigDict, Field


class BookBaseSchema(BaseModel):
    title: str
    author: str


class BookCreateSchema(BookBaseSchema):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)


class BookSchema(BookBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)
