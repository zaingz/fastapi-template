from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    description: str | None = Field(default=None, max_length=1000, description="Item description")
    price: float = Field(..., gt=0, description="Item price")


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, gt=0)


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    price: float


class ItemList(BaseModel):
    items: list[ItemResponse]
    total: int
