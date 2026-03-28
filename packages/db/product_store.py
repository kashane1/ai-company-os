from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.product import ProductRecord


class ProductStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.products_root)

    def save(self, product: ProductRecord) -> str:
        return str(self.store.save(product.id, product.to_dict()))

    def load(self, product_id: str) -> ProductRecord:
        return ProductRecord.from_dict(self.store.load(product_id))
