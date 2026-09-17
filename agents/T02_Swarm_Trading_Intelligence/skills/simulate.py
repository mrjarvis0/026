import uuid
import os
import sys

# Ensure downward imports by adjusting path if necessary or just importing directly
from agents.T02_Swarm_Trading_Intelligence.store.database import Database
from agents.T02_Swarm_Trading_Intelligence.intelligence.swarm import SwarmSimulator

def init_and_simulate(db_path: str = "swarm.db", price: float = 50000.0, price_change: float = 0.03):
    """
    Initializes the swarm if not already created, then triggers a market reaction.
    """
    db = Database(db_path=db_path)
    simulator = SwarmSimulator(db)

    # Check if swarm is already initialized
    bots = db.get_all_bots()
    if len(bots) < 1000:
        print("Initializing swarm of 1000 bots...")
        simulator.initialize_swarm(1000)

    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    print(f"Triggering trade event {event_id} at price ${price:.2f} ({price_change*100:.1f}%)")

    summary = simulator.process_trade_event(event_id, price, price_change)
    return {
        'event_id': event_id,
        'summary': summary
    }
