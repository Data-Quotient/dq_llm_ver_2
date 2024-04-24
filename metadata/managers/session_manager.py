from dataclasses import dataclass, field
from typing import Any

@dataclass
class UserSession:
    session_id: str
    auth_token: str
    datasource_id: int
    ai_client: Any = field(default=None)
