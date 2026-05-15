from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class NotificationPayloadDto:
    event: str
    action: str
    sub_action: str
    trigger: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    body: Optional[str] = None
