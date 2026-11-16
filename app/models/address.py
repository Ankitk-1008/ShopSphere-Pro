
from app.core.database import Base
from app.models.resources import Addresses


class Address:
    pass


# Map the existing SQLAlchemy Table to this ORM class.
Base.registry.map_imperatively(Address, Addresses)
