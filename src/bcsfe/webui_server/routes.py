from __future__ import annotations

from .route_modules import base_routes  # noqa: F401
from .route_modules import cats_routes  # noqa: F401
from .route_modules import enemy_routes  # noqa: F401
from .route_modules import gamatoto_routes  # noqa: F401
from .route_modules import inventory_routes  # noqa: F401
from .route_modules import operation_routes  # noqa: F401
from .route_modules import progress_routes  # noqa: F401
from .route_modules import system_routes  # noqa: F401
from .route_modules import transfer_routes  # noqa: F401
from .route_modules import validation_routes  # noqa: F401

__all__ = [
    "base_routes",
    "cats_routes",
    "enemy_routes",
    "gamatoto_routes",
    "inventory_routes",
    "operation_routes",
    "progress_routes",
    "system_routes",
    "transfer_routes",
    "validation_routes",
]
