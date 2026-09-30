"""Repository layer — data access and persistence.

Imports Types and Config only.
"""

from app.repository.billing_repository import (
    create_billing_record,
    list_billing_records_for_subscription,
)
from app.repository.dealer_repository import get_dealer_by_code
from app.repository.plan_repository import (
    create_plan_version,
    get_published_version,
    list_versions,
    publish_plan_version,
)
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
    "create_billing_record",
    "create_plan_version",
    "create_subscriber",
    "create_subscription",
    "create_user",
    "get_dealer_by_code",
    "get_published_version",
    "get_subscriber_by_id",
    "get_subscriber_by_mobile",
    "get_user_by_id",
    "get_user_by_mobile",
    "get_user_by_username",
    "list_billing_records_for_subscription",
    "list_versions",
    "publish_plan_version",
]
