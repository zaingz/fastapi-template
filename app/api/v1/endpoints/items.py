from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.schemas.items import ItemCreate, ItemList, ItemResponse, ItemUpdate
from app.services.items import ItemService, get_item_service

router = APIRouter()

ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]


@router.get("/", response_model=ItemList, summary="List all items")
async def list_items(service: ItemServiceDep) -> ItemList:
    """Returns a list of all items."""
    return service.list_items()


@router.get("/{item_id}", response_model=ItemResponse, summary="Get an item")
async def get_item(item_id: str, service: ItemServiceDep) -> ItemResponse:
    """Returns a single item by ID."""
    return service.get_item(item_id)


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
)
async def create_item(data: ItemCreate, service: ItemServiceDep) -> ItemResponse:
    """Creates a new item and returns it."""
    return service.create_item(data)


@router.patch("/{item_id}", response_model=ItemResponse, summary="Update an item")
async def update_item(item_id: str, data: ItemUpdate, service: ItemServiceDep) -> ItemResponse:
    """Partially updates an item."""
    return service.update_item(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an item")
async def delete_item(item_id: str, service: ItemServiceDep) -> None:
    """Deletes an item by ID."""
    service.delete_item(item_id)
