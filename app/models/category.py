
from app.core.database import Base
from app.models.resources import Categories


class Category:
    pass


Base.registry.map_imperatively(Category, Categories)
