"""Repository layer — data access and persistence.

Imports Types and Config only.
"""

from app.repository.dealer_repository import get_dealer_by_code
from app.repository.schema import apply_schema
from app.repository.subscriber_repository import (
    create_subscriber,
    create_subscription,
    get_subscriber_by_id,
    get_subscriber_by_mobile,
)
from app.repository.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_mobile,
    get_user_by_username,
)

__all__ = [
    "apply_schema",
    "create_subscriber",
    "create_subscription",
    "create_user",
    "get_dealer_by_code",
    "get_subscriber_by_id",
    "get_subscriber_by_mobile",
    "get_user_by_id",
    "get_user_by_mobile",
    "get_user_by_username",
]
