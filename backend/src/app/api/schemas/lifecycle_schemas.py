"""Pydantic request/response models for the suspend/resume + port-out
API (E5-S4), extended with termination (E6-S6).

API layer.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.types.enums import SubscriberState


class TerminateRequest(BaseModel):
    """POST .../terminate request body. reason_code is mandatory —
    Field(min_length=1) rejects an empty one with a clean 422 before
    termination_service's own (defense-in-depth) ValueError check would
    otherwise be reached.
    """

    reason_code: str = Field(min_length=1)


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
