from pydantic import BaseModel, Field


class DevUploadResponse(BaseModel):
    request_id: int
    status: str = Field(default="accepted")
