from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

@dataclass
class Order:
    id: int
    client: Optional[str]
    total: Optional[Decimal]
    ip_address: Optional[str]
    affiliate_token: Optional[str]
    created_at: datetime
    notified: bool = False
    
    def __post_init__(self):
        # Convert string datetime to datetime object if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        
        # Convert float to Decimal for total
        if isinstance(self.total, float):
            self.total = Decimal(str(self.total))
