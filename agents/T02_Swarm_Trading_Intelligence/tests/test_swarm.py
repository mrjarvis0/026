import pytest
import os
import sqlite3
from agents.T02_Swarm_Trading_Intelligence.store.database import Database
from agents.T02_Swarm_Trading_Intelligence.intelligence.swarm import SwarmSimulator
from agents.T02_Swarm_Trading_Intelligence.skills.simulate import init_and_simulate

@pytest.fixture
def db():
    db_path = "test_swarm.db"
    database = Database(db_path=db_path)
    database.reset()
    yield database
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

def test_swarm_generation(db):
    simulator = SwarmSimulator(db)
    num_bots = simulator.initialize_swarm(1000)
    assert num_bots == 1000

    bots = db.get_all_bots()
    assert len(bots) == 1000

    # Check that strategies are assigned properly
    strategies = set([b.get('strategy') for b in bots])
    assert len(strategies) > 1
    assert 'noise_trader' in strategies
    assert 'momentum_chaser' in strategies

    # Verify parameter access using .get()
    for bot in bots[:10]:
        params = bot.get('parameters', {})
        assert isinstance(params, dict)

def test_swarm_reaction(db):
    simulator = SwarmSimulator(db)
    simulator.initialize_swarm(100) # smaller swarm for speed

    summary = simulator.process_trade_event("test_event_1", 50000.0, 0.05)

    assert 'buy' in summary
    assert 'sell' in summary
    assert 'hold' in summary
    assert summary['buy'] + summary['sell'] + summary['hold'] == 100

    # Verify reactions in db
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM reactions WHERE trade_event_id='test_event_1'")
        count = cursor.fetchone()[0]
        assert count == 100

def test_database_chunking(db):
    # This explicitly tests the batching logic limits. We will add 1500 bots.
    bots = []
    for i in range(1500):
        bots.append({
            'bot_id': f'bot_{i}',
            'strategy': 'random',
            'parameters': {}
        })
    db.insert_bots(bots)

    db_bots = db.get_all_bots()
    assert len(db_bots) == 1500

    bot_ids = [b.get('bot_id') for b in db_bots]
    fetched_bots = db.get_bots_by_ids(bot_ids)
    assert len(fetched_bots) == 1500

def test_simulate_skill():
    db_path = "test_simulate.db"
    db = Database(db_path)
    db.reset()

    result = init_and_simulate(db_path, 50000.0, 0.02)
    assert result['event_id'].startswith('evt_')

    assert sum(result['summary'].values()) == 1000

    if os.path.exists(db_path):
        os.remove(db_path)
