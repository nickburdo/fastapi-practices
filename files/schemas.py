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
