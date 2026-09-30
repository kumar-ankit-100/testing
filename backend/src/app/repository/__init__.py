"""Repository layer — data access and persistence.

Imports Types and Config only.
"""

from app.repository.billing_repository import (
    create_billing_record,
    list_billing_records_for_subscription,
)
from app.repository.csr_override_repository import (
    create_csr_override,
    list_csr_overrides_for_subscription,
)
from app.repository.dealer_repository import get_dealer_by_code
from app.repository.plan_repository import (
    create_plan_version,
    get_published_version,
    list_versions,
    publish_plan_version,
)
from app.repository.port_out_repository import (
    close_port_out_event,
    create_port_out_event,
    get_active_port_out_event,
)
from app.repository.reporting_repository import (
    activation_funnel_counts,
    arpu_trend,
    monthly_churn_rate,
    plan_mix_distribution,
)
from app.repository.schema import apply_schema
from app.repository.state_transition_repository import (
    append_state_transition,
    list_state_transitions_for_subscription,
)
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
    "activation_funnel_counts",
    "append_state_transition",
    "apply_schema",
    "arpu_trend",
    "close_port_out_event",
    "create_billing_record",
    "create_csr_override",
    "create_plan_version",
    "create_port_out_event",
    "create_subscriber",
    "create_subscription",
    "create_user",
    "get_active_port_out_event",
    "get_dealer_by_code",
    "get_published_version",
    "get_subscriber_by_id",
    "get_subscriber_by_mobile",
    "get_user_by_id",
    "get_user_by_mobile",
    "get_user_by_username",
    "list_billing_records_for_subscription",
    "list_csr_overrides_for_subscription",
    "list_state_transitions_for_subscription",
    "list_versions",
    "monthly_churn_rate",
    "plan_mix_distribution",
    "publish_plan_version",
]
