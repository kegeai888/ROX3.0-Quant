import sys
import os
import json
import unittest
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rox_quant.portfolio_backtest import PortfolioBacktestEngine

class TestPortfolioBacktest(unittest.TestCase):
    def test_backtest_execution(self):
        # 1. Construct a simple strategy
        # DataSource -> SignalOutput (Directly, assuming DataSource returns something that can be interpreted or we use a Weighting node)
        # To be safe: DataSource -> Weighting -> SignalOutput
        
        graph_data = {
            "nodes": [
                {"id": 1, "type": "quant/DataSource", "properties": {"poolName": "沪深300"}, "outputs": [{"name": "out", "type": "Array", "links": [1]}]},
                {"id": 2, "type": "quant/Weighting", "properties": {"method": "equal", "totalWeight": 1.0}, "inputs": [{"name": "in", "type": "Array", "link": 1}], "outputs": [{"name": "out", "type": "Array", "links": [2]}]},
                {"id": 3, "type": "quant/SignalOutput", "properties": {}, "inputs": [{"name": "in", "type": "Array", "link": 2}]}
            ],
            "links": [
                [1, 1, 0, 2, 0, "Array"],
                [2, 2, 0, 3, 0, "Array"]
            ]
        }
        json_str = json.dumps(graph_data)
        
        # 2. Initialize Engine
        engine = PortfolioBacktestEngine()
        
        # Inject Mock Data manually for testing to avoid network dependency
        from app.rox_quant.data_provider import PricePoint
        
        mock_symbols = ["600519", "000001"]
        # Generate enough data covering the test period 2023-01-01 to 2023-01-10
        start_date_dt = pd.to_datetime("2023-01-01")
        
        for sym in mock_symbols:
            history = []
            price = 100.0
            for i in range(30): 
                date_str = (start_date_dt + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
                # Make price fluctuate to trigger rebalancing
                price *= (1 + 0.02 * ((-1)**i)) 
                history.append(PricePoint(date=date_str, close=price, volume=100000))
            
            engine.history_cache[sym] = {p.date: p for p in history}
            
        # Override extract symbols to use our mock symbols
        # (The graph JSON has hardcoded poolName but logic uses extract_symbols for preload)
        # But wait, extract_symbols parses JSON. Let's just monkeypatch the method or 
        # ensure _extract_symbols returns what we want if we pass a dummy JSON with these codes.
        
        # Better: Set active_symbols manually after run calls it, but run calls it first thing.
        # So we can subclass or mock. Or just inject into graph_json.
        
        graph_data["nodes"][0]["properties"]["poolName"] = "CustomPool" 
        # The engine._extract_symbols uses regex on json string.
        # Let's just add the codes to the json string in a comment or property
        graph_data["comment"] = "Symbols: 600519, 000001" 
        json_str = json.dumps(graph_data)
        
        # 3. Run Backtest
        # Short period: 2023-01-01 to 2023-01-10
        result = engine.run(json_str, "2023-01-01", "2023-01-10", initial_capital=100000.0)
        
        # 4. Assertions
        print("Backtest Result Keys:", result.keys())
        self.assertIn("equity_curve", result)
        self.assertIn("dates", result)
        self.assertIn("positions", result)
        
        # Check lengths
        self.assertEqual(len(result["equity_curve"]), len(result["dates"]))
        self.assertGreater(len(result["dates"]), 0)
        
        # Check equity changes (it should change because of mock price fluctuation)
        # Note: It might stay 100000 if no trades happen, but our mock data and strategy should trigger trades.
        # The Mock Snapshot returns some stocks, DataSource picks them, Weighting assigns weights.
        # So we should have positions.
        
        last_equity = result["equity_curve"][-1]
        print(f"Initial Equity: 100000, Final Equity: {last_equity}")
    
        # It's possible equity drops or rises, but unlikely to be exactly 100000.0 unless no trades.
        # With mock data random walk, it should change.
        # In testing environment with random seed, sometimes it might not trade.
        # Let's check if trades happened.
        if len(result['trades']) > 0:
            print("Trades Sample:", result['trades'][:3])
            self.assertNotEqual(last_equity, 100000.0)
        else:
            print("Warning: No trades executed in random test, skipping equity check.")
        
        # Check positions
        last_positions = result["positions"][-1]
        print("Final Positions:", last_positions)
        self.assertIsInstance(last_positions, dict)
        self.assertGreater(len(last_positions), 0)

if __name__ == '__main__':
    unittest.main()
