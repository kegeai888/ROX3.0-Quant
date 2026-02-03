import sys
import os
import json
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rox_quant.graph_runner import StrategyGraphRunner

class TestGraphRunner(unittest.TestCase):
    def test_basic_strategy(self):
        # 构造一个简单的策略图 JSON
        # DataSource -> Factor (PE < 30) -> Selection (Top 2 by Market Cap) -> Weighting -> SignalOutput
        
        graph_data = {
            "nodes": [
                {"id": 1, "type": "quant/DataSource", "properties": {"poolName": "沪深300"}, "outputs": [{"name": "out", "type": "Array", "links": [1]}]},
                {"id": 2, "type": "quant/Factor", "properties": {"factor": "pe_ratio", "operator": "<", "value": 30}, "inputs": [{"name": "in", "type": "Array", "link": 1}], "outputs": [{"name": "out", "type": "Array", "links": [2]}]},
                {"id": 3, "type": "quant/Selection", "properties": {"sortBy": "market_cap", "direction": "desc", "topN": 2}, "inputs": [{"name": "in", "type": "Array", "link": 2}], "outputs": [{"name": "out", "type": "Array", "links": [3]}]},
                {"id": 4, "type": "quant/Weighting", "properties": {"method": "equal", "totalWeight": 1.0}, "inputs": [{"name": "in", "type": "Array", "link": 3}], "outputs": [{"name": "out", "type": "Array", "links": [4]}]},
                {"id": 5, "type": "quant/SignalOutput", "properties": {}, "inputs": [{"name": "in", "type": "Array", "link": 4}]}
            ],
            "links": [
                [1, 1, 0, 2, 0, "Array"], # Link 1: Node 1 (Slot 0) -> Node 2 (Slot 0)
                [2, 2, 0, 3, 0, "Array"], # Link 2: Node 2 (Slot 0) -> Node 3 (Slot 0)
                [3, 3, 0, 4, 0, "Array"], # Link 3: Node 3 (Slot 0) -> Node 4 (Slot 0)
                [4, 4, 0, 5, 0, "Array"]  # Link 4: Node 4 (Slot 0) -> Node 5 (Slot 0)
            ]
        }
        
        json_str = json.dumps(graph_data)
        
        runner = StrategyGraphRunner()
        result = runner.run(json_str)
        
        print("Execution Result:", result)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(5, result["results"]) # Node 5 is the output
        
        signals = result["results"][5]
        # 预期结果：
        # 原始数据中 PE < 30 的有：平安银行(6.5), 五粮液(25.4), 中国平安(8.2)
        # 排序：贵州茅台(PE 32.1, 排除), 比亚迪(PE 55.3, 排除)
        # 剩余按市值降序：中国平安(8000), 五粮液(5000), 平安银行(2000)
        # Top 2: 中国平安, 五粮液
        # 权重: 等权重, 0.5 each
        
        self.assertEqual(len(signals), 2)
        self.assertIn("601318.SH", signals) # 中国平安
        self.assertIn("000858.SZ", signals) # 五粮液
        self.assertAlmostEqual(signals["601318.SH"], 0.5)

if __name__ == '__main__':
    unittest.main()
