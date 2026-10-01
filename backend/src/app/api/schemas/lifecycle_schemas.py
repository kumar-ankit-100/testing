"""Pydantic response models for the suspend/resume + port-out API (E5-S4).

API layer.
"""

from datetime import datetime

from pydantic import BaseModel

from app.types.enums import SubscriberState


class LifecycleStateResponse(BaseModel):
    """POST .../suspend, .../resume, .../port-out/cancel 200 response."""

    subscription_id: str
    state: SubscriberState


class PortOutEventResponse(BaseModel):
    """POST .../port-out/{request,finalize} 200 response."""

    port_out_event_id: str
    subscription_id: str
    requested_at: datetime
    cooling_period_end_at: datetime
    status: str
