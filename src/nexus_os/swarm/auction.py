"""auction.py — Auction-Based Swarm Allocation

Agent auction system for task allocation. Agents bid on tasks based on capability and load.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class BidStatus(Enum):
    """Bid status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Bid:
    """Agent bid for a task."""
    bid_id: str
    agent_id: str
    task_id: str
    bid_amount: float  # Lower = more willing
    capability_score: float
    load_factor: float  # 0.0 = idle, 1.0 = max load
    created_at: float
    status: BidStatus = BidStatus.PENDING


@dataclass
class TaskAuction:
    """Auction for a task."""
    auction_id: str
    task_id: str
    task_type: str
    min_budget: float
    deadline: float
    bids: List[Bid] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    winning_bid: Optional[Bid] = None


class AuctionHouse:
    """
    Auction-based swarm allocation.
    
    Features:
    - Create task auctions
    - Receive bids from agents
    - Resolve auctions (lowest bid wins, weighted by capability)
    - Auto-expiration
    """
    
    def __init__(
        self,
        bid_timeout_seconds: float = 60.0,
        capability_weight: float = 0.6,
    ):
        self.bid_timeout = bid_timeout_seconds
        self.capability_weight = capability_weight
        
        self._auctions: Dict[str, TaskAuction] = {}
        self._lock = threading.RLock()
    
    def create_auction(
        self,
        task_id: str,
        task_type: str,
        min_budget: float = 0.0,
        deadline: Optional[float] = None,
    ) -> str:
        """Create a new task auction."""
        auction_id = f"auction-{uuid.uuid4().hex[:12]}"
        
        auction = TaskAuction(
            auction_id=auction_id,
            task_id=task_id,
            task_type=task_type,
            min_budget=min_budget,
            deadline=deadline or (time.time() + self.bid_timeout),
        )
        
        with self._lock:
            self._auctions[auction_id] = auction
        
        logger.info(f"Created auction {auction_id} for task {task_id}")
        return auction_id
    
    def submit_bid(
        self,
        auction_id: str,
        agent_id: str,
        bid_amount: float,
        capability_score: float = 1.0,
        load_factor: float = 0.0,
    ) -> Optional[str]:
        """Submit a bid to an auction."""
        with self._lock:
            auction = self._auctions.get(auction_id)
            if auction is None or auction.resolved:
                return None
            
            if time.time() > auction.deadline:
                return None
            
            bid_id = f"bid-{uuid.uuid4().hex[:12]}"
            bid = Bid(
                bid_id=bid_id,
                agent_id=agent_id,
                task_id=auction.task_id,
                bid_amount=bid_amount,
                capability_score=capability_score,
                load_factor=load_factor,
                created_at=time.time(),
            )
            
            auction.bids.append(bid)
            logger.info(f"Agent {agent_id} bid {bid_amount} on auction {auction_id}")
            return bid_id
    
    def resolve_auction(self, auction_id: str) -> Optional[Bid]:
        """Resolve auction - select winning bid."""
        with self._lock:
            auction = self._auctions.get(auction_id)
            if auction is None or auction.resolved:
                return None
            
            if not auction.bids:
                return None
            
            # Score: lower bid_amount is better, higher capability is better
            # Composite = bid_amount * (1 - capability_weight * capability_score) * (1 + load_factor)
            best_bid = None
            best_score = float('inf')
            
            for bid in auction.bids:
                # Normalize scores
                cap_factor = 1.0 - self.capability_weight * bid.capability_score
                load_factor = 1.0 + bid.load_factor * 0.5
                score = bid.bid_amount * cap_factor * load_factor
                
                if score < best_score:
                    best_score = score
                    best_bid = bid
            
            if best_bid:
                best_bid.status = BidStatus.ACCEPTED
                auction.winning_bid = best_bid
                auction.resolved = True
                logger.info(f"Auction {auction_id} won by {best_bid.agent_id}")
            
            return best_bid
    
    def get_auction(self, auction_id: str) -> Optional[TaskAuction]:
        """Get auction details."""
        with self._lock:
            return self._auctions.get(auction_id)
    
    def get_bids(self, auction_id: str) -> List[Bid]:
        """Get all bids for an auction."""
        with self._lock:
            auction = self._auctions.get(auction_id)
            return auction.bids if auction else []
    
    def expire_auctions(self) -> int:
        """Expire old auctions."""
        now = time.time()
        expired = 0
        
        with self._lock:
            for auction in list(self._auctions.values()):
                if not auction.resolved and now > auction.deadline:
                    auction.resolved = True
                    for bid in auction.bids:
                        bid.status = BidStatus.EXPIRED
                    expired += 1
        
        return expired


# ── Singleton ────────────────────────────────────────────────────────────

_auction_instance: Optional[AuctionHouse] = None
_auction_lock = threading.Lock()


def get_auction_house() -> AuctionHouse:
    """Get or create AuctionHouse singleton."""
    global _auction_instance
    if _auction_instance is None:
        with _auction_lock:
            if _auction_instance is None:
                _auction_instance = AuctionHouse()
    return _auction_instance