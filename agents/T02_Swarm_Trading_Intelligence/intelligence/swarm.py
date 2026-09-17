import random
import uuid
from typing import List, Dict, Any

class SwarmSimulator:
    def __init__(self, db):
        self.db = db

    def initialize_swarm(self, num_bots: int = 1000):
        """Procedurally generates the swarm and stores them in the db."""
        strategies = ['trend_following', 'mean_reversion', 'contrarian', 'random']
        bots = []
        for _ in range(num_bots):
            strategy = random.choice(strategies)
            params = {}
            if strategy == 'trend_following':
                params['threshold'] = random.uniform(0.01, 0.05)
                params['aggressiveness'] = random.uniform(0.5, 1.5)
            elif strategy == 'mean_reversion':
                params['deviation_threshold'] = random.uniform(0.02, 0.08)
            elif strategy == 'contrarian':
                params['reversal_factor'] = random.uniform(0.8, 1.2)
            else:
                params['noise_level'] = random.uniform(0.1, 0.5)

            bots.append({
                'bot_id': f"bot_{uuid.uuid4().hex[:8]}",
                'strategy': strategy,
                'parameters': params
            })

        self.db.insert_bots(bots)
        return len(bots)

    def process_trade_event(self, trade_event_id: str, current_price: float, price_change_pct: float) -> Dict[str, Any]:
        """Simulates how the swarm reacts to a market event (e.g. user places a trade)."""
        bots = self.db.get_all_bots()
        reactions = []

        summary = {
            'buy': 0,
            'sell': 0,
            'hold': 0
        }

        for bot in bots:
            strategy = bot.get('strategy')
            params = bot.get('parameters', {})
            action = 'hold'

            if strategy == 'trend_following':
                threshold = params.get('threshold', 0.02)
                if price_change_pct > threshold:
                    action = 'buy'
                elif price_change_pct < -threshold:
                    action = 'sell'

            elif strategy == 'mean_reversion':
                dev_threshold = params.get('deviation_threshold', 0.05)
                if price_change_pct > dev_threshold:
                    action = 'sell'
                elif price_change_pct < -dev_threshold:
                    action = 'buy'

            elif strategy == 'contrarian':
                if price_change_pct > 0:
                    action = 'sell' if random.random() < 0.7 else 'hold'
                elif price_change_pct < 0:
                    action = 'buy' if random.random() < 0.7 else 'hold'

            else: # random
                r = random.random()
                if r < 0.33:
                    action = 'buy'
                elif r < 0.66:
                    action = 'sell'
                else:
                    action = 'hold'

            summary[action] += 1

            reactions.append({
                'bot_id': bot.get('bot_id'),
                'trade_event_id': trade_event_id,
                'action': action,
                'price': current_price
            })

        self.db.record_reactions(reactions)
        return summary
