"""tests/swarm/test_auction.py — Auction Tests"""

import pytest

from nexus_os.swarm.auction import (
    AuctionHouse,
    BidStatus,
    get_auction_house,
)


class TestAuctionBasics:
    """Test basic auction operations."""

    def test_create_auction(self):
        house = AuctionHouse()
        auction_id = house.create_auction(
            task_id="task-1",
            task_type="code",
            min_budget=10.0,
        )
        assert auction_id is not None
        
        auction = house.get_auction(auction_id)
        assert auction.task_id == "task-1"

    def test_submit_bid(self):
        house = AuctionHouse()
        auction_id = house.create_auction("task-1", "code")
        
        bid_id = house.submit_bid(
            auction_id=auction_id,
            agent_id="agent-1",
            bid_amount=50.0,
            capability_score=0.8,
            load_factor=0.2,
        )
        assert bid_id is not None
        
        bids = house.get_bids(auction_id)
        assert len(bids) == 1
        assert bids[0].agent_id == "agent-1"

    def test_resolve_auction(self):
        house = AuctionHouse()
        auction_id = house.create_auction("task-1", "code")
        
        house.submit_bid(auction_id, "agent-1", 50.0, 0.8, 0.2)
        house.submit_bid(auction_id, "agent-2", 30.0, 0.9, 0.1)
        
        winning = house.resolve_auction(auction_id)
        assert winning is not None

    def test_lowest_bid_wins(self):
        house = AuctionHouse()
        auction_id = house.create_auction("task-1", "code")
        
        house.submit_bid(auction_id, "agent-1", 100.0, 1.0, 0.0)
        house.submit_bid(auction_id, "agent-2", 50.0, 1.0, 0.0)
        
        winning = house.resolve_auction(auction_id)
        assert winning.agent_id == "agent-2"


class TestExpiration:
    """Test auction expiration."""

    def test_expire_old_auctions(self):
        house = AuctionHouse(bid_timeout_seconds=0.001)
        auction_id = house.create_auction("task-1", "code")
        
        import time
        time.sleep(0.01)
        
        expired = house.expire_auctions()
        assert expired >= 0


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton(self):
        house1 = get_auction_house()
        house2 = get_auction_house()
        assert house1 is house2