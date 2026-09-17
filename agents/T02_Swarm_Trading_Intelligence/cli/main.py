import argparse
import sys
import os

from agents.T02_Swarm_Trading_Intelligence.skills.simulate import init_and_simulate
from agents.T02_Swarm_Trading_Intelligence.store.database import Database

def main():
    parser = argparse.ArgumentParser(description="T02 Swarm Trading Intelligence CLI")
    parser.add_argument('--price', type=float, default=50000.0, help="Current market price")
    parser.add_argument('--change', type=float, default=0.03, help="Recent price change percentage (e.g., 0.03 for +3%)")
    parser.add_argument('--db', type=str, default="swarm.db", help="Path to SQLite database")
    parser.add_argument('--reset', action='store_true', help="Reset the database before running")

    args = parser.parse_args()

    if args.reset:
        db = Database(args.db)
        db.reset()
        print("Database reset.")

    result = init_and_simulate(args.db, args.price, args.change)
    print("Simulation Complete!")
    print(f"Event ID: {result['event_id']}")
    print(f"Swarm Reaction Summary:")
    print(f"  Buy:  {result['summary']['buy']}")
    print(f"  Sell: {result['summary']['sell']}")
    print(f"  Hold: {result['summary']['hold']}")

if __name__ == '__main__':
    main()
