import os
import inspect
import json
import importlib.util
from typing import List, Dict, Any, Optional

class StrategyRepository:
    """
    Manages strategy discovery, metadata, and export.
    """
    def __init__(self, strategies_dir: str = "app/strategies"):
        self.strategies_dir = strategies_dir
        
    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        Scan directory for strategy classes.
        """
        results = []
        if not os.path.exists(self.strategies_dir):
            return results
            
        for filename in os.listdir(self.strategies_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                path = os.path.join(self.strategies_dir, filename)
                try:
                    # Dynamically load module
                    spec = importlib.util.spec_from_file_location(filename[:-3], path)
                    if not spec or not spec.loader: continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Inspect classes
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # Simple rule: class name must contain 'Strategy'
                        if "Strategy" in name:
                            doc = inspect.getdoc(obj) or "No description"
                            results.append({
                                "id": f"{filename[:-3]}.{name}",
                                "name": name,
                                "description": doc.split('\n')[0], # first line
                                "file": filename,
                                "author": "User" # Placeholder
                            })
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return results

    def export_strategy(self, strategy_id: str) -> Optional[str]:
        """
        Export a strategy to JSON (for sharing).
        """
        # strategy_id: "my_strategy.MyStrategy"
        # In reality, we'd read the file content
        return json.dumps({"id": strategy_id, "content": "Not implemented yet"})
