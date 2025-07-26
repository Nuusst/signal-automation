from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Affiliate:
    id: int
    phone_number: str
    token: str
    created_at: datetime
    is_active: bool = True
    
    def __post_init__(self):
        # Convert string datetime to datetime object if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
