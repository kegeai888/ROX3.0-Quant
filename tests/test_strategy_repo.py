import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rox_quant.strategy_repo import StrategyRepository

def test_repo():
    repo = StrategyRepository(strategies_dir="app/strategies")
    items = repo.list_strategies()
    print(f"Found {len(items)} strategies")
    for item in items:
        print(f"- {item['name']}: {item['description']}")
        
    if len(items) > 0:
        print("✅ Strategy Repo Test Passed")
    else:
        print("❌ Strategy Repo Test Failed")

if __name__ == "__main__":
    test_repo()
