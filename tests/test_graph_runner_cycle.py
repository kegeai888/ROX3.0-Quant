import sys
import os
import json
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rox_quant.graph_runner import StrategyGraphRunner

class TestGraphRunnerCycle(unittest.TestCase):
    def test_cycle_detection(self):
        # 构造一个带有环的策略图
        # Node 1 (DataSource) -> Node 2 (Factor) -> Node 3 (Factor) -> Node 2 (Loop!) -> ... -> SignalOutput
        
        # 但 LiteGraph 的链接通常是 Output -> Input。
        # A cycle implies: 
        # Node A output -> Node B input
        # Node B output -> Node A input
        
        # Node 1: DataSource
        # Node 2: Factor A (Input from 1)
        # Node 3: Factor B (Input from 2)
        # Node 4: Combine (Input from 3 AND 2) - This is valid DAG
        
        # Let's make a real cycle:
        # Node 2 inputs from Node 3
        # Node 3 inputs from Node 2
        # And Node 4 (Output) inputs from Node 3
        
        graph_data = {
            "nodes": [
                {"id": 1, "type": "quant/DataSource", "properties": {"poolName": "沪深300"}, "outputs": [{"name": "out", "type": "Array", "links": [1]}]},
                
                {"id": 2, "type": "quant/Factor", "properties": {}, "inputs": [{"name": "in", "type": "Array", "link": 2}], "outputs": [{"name": "out", "type": "Array", "links": [1]}]},
                
                {"id": 3, "type": "quant/Factor", "properties": {}, "inputs": [{"name": "in", "type": "Array", "link": 1}], "outputs": [{"name": "out", "type": "Array", "links": [2]}]},
                
                {"id": 4, "type": "quant/SignalOutput", "properties": {}, "inputs": [{"name": "in", "type": "Array", "link": 2}]}
            ],
            "links": [
                # Link 1: Node 2 (Slot 0) -> Node 3 (Slot 0)
                [1, 2, 0, 3, 0, "Array"],
                # Link 2: Node 3 (Slot 0) -> Node 2 (Slot 0) AND Node 4 (Slot 0)
                # Wait, one link usually connects one source to one target in simple JSON representation I assumed.
                # In LiteGraph JSON, links array is: [id, origin_id, origin_slot, target_id, target_slot, type]
                
                [1, 2, 0, 3, 0, "Array"], # Node 2 -> Node 3
                [2, 3, 0, 2, 0, "Array"], # Node 3 -> Node 2 (Cycle!)
                [3, 3, 0, 4, 0, "Array"]  # Node 3 -> Node 4 (Output)
            ]
        }
        
        json_str = json.dumps(graph_data)
        
        runner = StrategyGraphRunner()
        result = runner.run(json_str)
        
        print("Cycle Execution Result:", result)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Cycle detected", result["message"])

if __name__ == '__main__':
    unittest.main()
