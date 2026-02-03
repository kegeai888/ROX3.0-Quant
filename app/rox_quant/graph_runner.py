import json
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from app.rox_quant.data_provider import DataProvider

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyGraphRunner:
    """
    可视化策略图执行引擎。
    解析前端 LiteGraph.js 生成的 JSON，并执行策略逻辑。
    """
    
    def __init__(self):
        self.node_handlers = {
            "quant/DataSource": self._handle_data_source,
            "quant/Factor": self._handle_factor,
            "quant/Combine": self._handle_combine,
            "quant/Selection": self._handle_selection,
            "quant/Weighting": self._handle_weighting,
            "quant/SignalOutput": self._handle_signal_output,
        }
        # 存储节点执行结果的缓存
        self.execution_cache = {}
        # 用于循环检测
        self.visiting = set()
        
        # 初始化数据提供者
        self.data_provider = DataProvider()
        # 运行上下文
        self.context = {}

    def run(self, graph_json: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行策略图。
        
        Args:
            graph_json: JSON 格式的图数据字符串
            context: 运行上下文，可包含 'data' (DataFrame) 或 'date' (str)
            
        Returns:
            执行结果字典，包含最终的信号数据
        """
        try:
            self.context = context or {}
            
            graph_data = json.loads(graph_json)
            nodes = graph_data.get("nodes", [])
            links = graph_data.get("links", [])
            
            # 重置缓存和访问记录
            self.execution_cache = {}
            self.visiting = set()
            
            # 构建链接映射: target_node_id -> input_slot_index -> source_link_info
            # link 结构: [id, origin_id, origin_slot, target_id, target_slot, type]
            self.link_map = {}
            for link in links:
                link_id, origin_id, origin_slot, target_id, target_slot, type_ = link
                if target_id not in self.link_map:
                    self.link_map[target_id] = {}
                self.link_map[target_id][target_slot] = {
                    "origin_id": origin_id,
                    "origin_slot": origin_slot
                }
                
            # 找到所有节点并建立映射
            self.node_map = {node["id"]: node for node in nodes}
            
            # 找到输出节点（没有输出连接的节点，或者是明确的 SignalOutput 节点）
            # 在这里我们主要寻找 SignalOutput 节点来驱动执行
            output_nodes = [n for n in nodes if n["type"] == "quant/SignalOutput"]
            
            if not output_nodes:
                logger.warning("No SignalOutput node found in strategy graph.")
                return {"error": "No SignalOutput node found"}
            
            results = {}
            for node in output_nodes:
                # 每次从一个新的根节点开始执行时，理论上应该重置 visiting，
                # 但由于是DAG，且有 cache，全局 visiting 也是安全的，除非跨连通分量复用（这里不涉及）。
                # 为了保险，每次根调用前确保 visiting 为空（其实递归结束它就空了）
                self.visiting.clear()
                result = self._execute_node(node["id"])
                results[node["id"]] = result
                
            return {"status": "success", "results": results}
            
        except Exception as e:
            logger.error(f"Error executing strategy graph: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _execute_node(self, node_id: int) -> Any:
        """递归执行节点"""
        if node_id in self.execution_cache:
            return self.execution_cache[node_id]
        
        if node_id in self.visiting:
            raise RecursionError(f"Cycle detected at node {node_id}")
            
        self.visiting.add(node_id)
        
        try:
            node = self.node_map.get(node_id)
            if not node:
                raise ValueError(f"Node {node_id} not found")
                
            node_type = node.get("type")
            handler = self.node_handlers.get(node_type)
            
            if not handler:
                logger.warning(f"No handler for node type: {node_type}")
                return None
                
            # 准备输入数据
            inputs = []
            if node_id in self.link_map:
                # 获取该节点的所有输入连接
                # LiteGraph 的 inputs 数组顺序通常与 slot 顺序一致
                node_inputs_def = node.get("inputs", [])
                
                for i, input_def in enumerate(node_inputs_def):
                    link_info = self.link_map[node_id].get(i)
                    if link_info:
                        # 递归获取上游节点的结果
                        origin_val = self._execute_node(link_info["origin_id"])
                        inputs.append(origin_val)
                    else:
                        inputs.append(None)
            
            # 执行节点逻辑
            logger.info(f"Executing node {node_id} ({node_type})")
            result = handler(node, inputs)
            
            # 缓存结果
            self.execution_cache[node_id] = result
            return result
            
        finally:
            self.visiting.remove(node_id)

    # --- Node Handlers ---

    def _handle_data_source(self, node: Dict, inputs: List[Any]) -> pd.DataFrame:
        pool_name = node.get("properties", {}).get("poolName", "沪深300")
        logger.info(f"Data Source: {pool_name}")
        
        df_raw = None
        
        # 1. 优先使用 Context 中的数据 (用于回测)
        if self.context.get("data") is not None:
            logger.info("Using context data for strategy execution")
            df_raw = self.context["data"]
            
        # 2. 否则尝试从 DataProvider 获取实时数据
        if df_raw is None:
            try:
                df_raw = self.data_provider.get_all_market_data()
            except Exception as e:
                logger.error(f"Error fetching market data: {e}")
                df_raw = None
            
        if df_raw is None or df_raw.empty:
            logger.warning("Using mock data fallback.")
            # 模拟返回一个简单的 DataFrame
            data = {
                "symbol": ["000001.SZ", "600519.SH", "000858.SZ", "601318.SH", "002594.SZ"],
                "name": ["平安银行", "贵州茅台", "五粮液", "中国平安", "比亚迪"],
                "pe_ratio": [6.5, 32.1, 25.4, 8.2, 55.3],
                "market_cap": [2000, 21000, 5000, 8000, 7000] # 亿元
            }
            return pd.DataFrame(data)

        # 真实数据处理
        # 映射列名
        rename_map = {
            "代码": "symbol",
            "名称": "name",
            "最新价": "price",
            "市盈率-动态": "pe_ratio",
            "市净率": "pb_ratio",
            "总市值": "market_cap",
            "涨跌幅": "return_rate"
        }
        
        # 检查是否已经是标准列名（回测数据可能已经处理过）
        if "symbol" in df_raw.columns and "market_cap" in df_raw.columns:
            df = df_raw.copy()
        else:
            df = df_raw.rename(columns=rename_map)
        
        # 确保关键列存在
        for col in ["symbol", "name", "pe_ratio", "market_cap"]:
            if col not in df.columns:
                df[col] = 0.0
                
        # 数据类型转换
        numeric_cols = ["pe_ratio", "pb_ratio", "market_cap", "price", "return_rate"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        # 简单的股票池逻辑 (基于市值排序模拟)
        # 如果是 Context 数据，可能已经是一个子集，但为了安全再做一次筛选
        if pool_name == "沪深300":
             df = df.sort_values(by="market_cap", ascending=False).head(300)
        elif pool_name == "中证500":
             df = df.sort_values(by="market_cap", ascending=False).iloc[300:800]
        
        # 格式化 symbol
        def format_symbol(code):
            code = str(code).zfill(6)
            if "." in code: return code # Already formatted
            if code.startswith("6"): return f"{code}.SH"
            if code.startswith("0") or code.startswith("3"): return f"{code}.SZ"
            if code.startswith("4") or code.startswith("8"): return f"{code}.BJ"
            return code
            
        df["symbol"] = df["symbol"].apply(format_symbol)
        
        logger.info(f"Fetched {len(df)} stocks for pool {pool_name}")
        return df

    def _handle_factor(self, node: Dict, inputs: List[Any]) -> pd.DataFrame:
        input_df = inputs[0] if inputs else None
        if input_df is None or not isinstance(input_df, pd.DataFrame):
            return None
            
        props = node.get("properties", {})
        factor = props.get("factor", "pe_ratio")
        operator = props.get("operator", "<")
        value = float(props.get("value", 30))
        
        logger.info(f"Filtering: {factor} {operator} {value}")
        
        # 简单的 pandas 筛选
        try:
            if operator == "<":
                return input_df[input_df[factor] < value]
            elif operator == ">":
                return input_df[input_df[factor] > value]
            elif operator == "=":
                return input_df[input_df[factor] == value]
            elif operator == "<=":
                return input_df[input_df[factor] <= value]
            elif operator == ">=":
                return input_df[input_df[factor] >= value]
        except KeyError:
            logger.error(f"Factor {factor} not found in data")
            return input_df
            
        return input_df

    def _handle_combine(self, node: Dict, inputs: List[Any]) -> pd.DataFrame:
        df_a = inputs[0] if len(inputs) > 0 else None
        df_b = inputs[1] if len(inputs) > 1 else None
        
        operation = node.get("properties", {}).get("operation", "AND")
        
        if df_a is None: return df_b
        if df_b is None: return df_a
        
        # 假设基于 symbol 进行合并
        if operation == "AND":
            # 交集
            return pd.merge(df_a, df_b, on="symbol", how="inner", suffixes=("", "_drop")).filter(regex="^(?!.*_drop)")
        elif operation == "OR":
            # 并集
            return pd.concat([df_a, df_b]).drop_duplicates(subset="symbol")
            
        return df_a

    def _handle_selection(self, node: Dict, inputs: List[Any]) -> pd.DataFrame:
        input_df = inputs[0] if inputs else None
        if input_df is None: return None
        
        props = node.get("properties", {})
        sort_by = props.get("sortBy", "market_cap")
        direction = props.get("direction", "desc")
        top_n = int(props.get("topN", 10))
        
        ascending = (direction == "asc")
        
        try:
            sorted_df = input_df.sort_values(by=sort_by, ascending=ascending)
            return sorted_df.head(top_n)
        except KeyError:
            logger.error(f"Column {sort_by} not found for sorting")
            return input_df.head(top_n)

    def _handle_weighting(self, node: Dict, inputs: List[Any]) -> pd.DataFrame:
        input_df = inputs[0] if inputs else None
        if input_df is None: return None
        
        props = node.get("properties", {})
        method = props.get("method", "equal")
        total_weight = float(props.get("totalWeight", 1.0))
        
        df = input_df.copy()
        count = len(df)
        
        if count == 0:
            return df
            
        if method == "equal":
            df["weight"] = total_weight / count
        elif method == "market_cap":
            if "market_cap" in df.columns:
                total_mc = df["market_cap"].sum()
                df["weight"] = (df["market_cap"] / total_mc) * total_weight
            else:
                df["weight"] = total_weight / count # Fallback
                
        return df

    def _handle_signal_output(self, node: Dict, inputs: List[Any]) -> Dict:
        input_df = inputs[0] if inputs else None
        if input_df is None: return {}
        
        # 转换为简单的字典格式返回: symbol -> weight
        if "weight" in input_df.columns:
            signal_data = input_df.set_index("symbol")["weight"].to_dict()
        else:
            # 默认为等权重
            symbols = input_df["symbol"].tolist()
            weight = 1.0 / len(symbols) if symbols else 0
            signal_data = {s: weight for s in symbols}
            
        # --- Event Bus Integration ---
        try:
            import asyncio
            # Check if there is a running loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
                
            if loop and loop.is_running():
                from app.core.event_bus import EventBus
                # Publish signal asynchronously
                loop.create_task(EventBus().publish("strategy_signals", {
                    "source": "strategy_engine",
                    "node_id": node.get("id"),
                    "signals": signal_data,
                    "timestamp": pd.Timestamp.now().isoformat()
                }))
        except Exception as e:
            logger.warning(f"Failed to publish strategy signal: {e}")
            
        return signal_data
