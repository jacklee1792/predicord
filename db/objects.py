from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Market:
    id: int  # auto
    name: str
    creator_id: int
    created_at: int  # auto
    outcome: str
    payout_cents: Optional[int]
    resolved_at: Optional[int]


@dataclass
class Order:
    id: int  # auto
    market_id: int
    user_id: int
    order_type: Literal["market", "limit"]
    order_direction: Literal["buy", "sell"]
    price_cents: int
    quantity: int
    created_at: int  # auto
    expires_at: int


@dataclass
class Trade:
    id: int  # auto
    market_id: int
    buyer_id: int
    seller_id: int
    price_cents: int
    quantity: int
    timestamp: int


@dataclass
class User:
    id: int
    display_name: str
    avatar_hash: str
