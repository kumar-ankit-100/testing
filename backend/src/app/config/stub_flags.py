"""Default values for TelcoLane's deterministic stub integrations.

Config layer — imports Types only (here: nothing, pure constants).

KYC, dealer-code validation, and MNP are all stubbed per system-design.md
section on stub integrations: no external network calls, only deterministic
in-process flags. These constants are the single source of truth for their
defaults so no other module hardcodes the same literal.
"""

DEFAULT_KYC_STUB_VERIFIED: bool = True
DEFAULT_MNP_STUB_SUCCESS: bool = True
DEFAULT_DEALER_FAIL_CODE: str = "DEALER-FAIL"
