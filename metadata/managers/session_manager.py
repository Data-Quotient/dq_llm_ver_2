from dataclasses import dataclass, field
from typing import Any
import asyncio

@dataclass
class UserSession:
    session_id: str
    auth_token: str
    datasource_id: int
    ai_client: Any = field(default=None)
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)