import uuid

from app.api.v1.schemas.items import ItemCreate, ItemList, ItemResponse, ItemUpdate
from app.core.exceptions import NotFoundError

# In-memory store — swap for a repository when DB is added
_ITEMS: dict[str, dict] = {}


class ItemService:
    """Item business logic. No HTTP primitives here."""

    def list_items(self) -> ItemList:
        items = list(_ITEMS.values())
        return ItemList(items=items, total=len(_ITEMS))

    def get_item(self, item_id: str) -> ItemResponse:
        if item_id not in _ITEMS:
            raise NotFoundError(resource="Item", identifier=item_id)
        return ItemResponse(**_ITEMS[item_id])

    def create_item(self, data: ItemCreate) -> ItemResponse:
        item_id = str(uuid.uuid4())
        item = {"id": item_id, **data.model_dump()}
        _ITEMS[item_id] = item
        return ItemResponse(**item)

    def update_item(self, item_id: str, data: ItemUpdate) -> ItemResponse:
        if item_id not in _ITEMS:
            raise NotFoundError(resource="Item", identifier=item_id)
        update_data = data.model_dump(exclude_unset=True)
        _ITEMS[item_id].update(update_data)
        return ItemResponse(**_ITEMS[item_id])

    def delete_item(self, item_id: str) -> None:
        if item_id not in _ITEMS:
            raise NotFoundError(resource="Item", identifier=item_id)
        del _ITEMS[item_id]


def get_item_service() -> ItemService:
    """Factory function for DI. Swap for class with DB session when extending."""
    return ItemService()
