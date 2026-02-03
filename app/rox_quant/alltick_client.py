import json
import threading
import time
import websocket
import ssl
from typing import Dict, List, Callable, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

class AllTickClient:
    """
    Client for AllTick WebSocket API (Real-time Market Data).
    Supports A-share, HK stocks, US stocks, Forex, Crypto, etc.
    """
    
    WS_URL = "wss://quote.alltick.co/quote-stock-b-ws-api"
    
    def __init__(self, token: str):
        self.token = token
        self.ws_url = f"{self.WS_URL}?token={self.token}"
        self.ws: Optional[websocket.WebSocketApp] = None
        self.wst: Optional[threading.Thread] = None
        self.is_connected = False
        self.callbacks: List[Callable] = []
        self.subscribed_symbols: Dict[str, int] = {} # code -> depth_level
        self.latest_ticks: Dict[str, dict] = {} # code -> tick_data
        self._trace_id = 0
        
    def _get_trace(self):
        self._trace_id += 1
        return f"rox_quant_{self._trace_id}"

    def connect(self):
        """Start the WebSocket connection in a separate thread."""
        if self.is_connected:
            return

        logger.info(f"Connecting to AllTick WS: {self.WS_URL}")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.wst = threading.Thread(target=self.ws.run_forever, kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
        self.wst.daemon = True
        self.wst.start()

    def disconnect(self):
        """Close the WebSocket connection."""
        if self.ws:
            self.ws.close()
        self.is_connected = False

    def subscribe(self, symbols: List[str], depth_level: int = 5):
        """
        Subscribe to market depth/tick data for a list of symbols.
        
        Args:
            symbols: List of symbol codes (e.g., ["700.HK", "AAPL.US", "600519.SH"])
            depth_level: Depth level (e.g., 5 for 5-level order book)
        """
        if not symbols:
            return

        # Update local subscription list
        for s in symbols:
            self.subscribed_symbols[s] = depth_level
            
        if self.is_connected:
            self._send_subscription(symbols, depth_level)

    def _send_subscription(self, symbols: List[str], depth_level: int):
        symbol_list = [{"code": s, "depth_level": depth_level} for s in symbols]
        
        # Use modulo to ensure seq_id doesn't overflow 32-bit int
        seq_id = int(time.time() * 1000) % 2147483647
        
        payload = {
            "cmd_id": 22002, # Subscribe
            "seq_id": seq_id,
            "trace": self._get_trace(),
            "data": {
                "symbol_list": symbol_list
            }
        }
        try:
            self.ws.send(json.dumps(payload))
            logger.info(f"Subscribed to {symbols}")
        except Exception as e:
            logger.error(f"Failed to send subscription: {e}")

    def add_callback(self, callback: Callable):
        """Add a callback function to handle incoming data."""
        self.callbacks.append(callback)

    def _on_open(self, ws):
        logger.info("AllTick WS Connected")
        self.is_connected = True
        
        # Resubscribe if we have pending subscriptions
        if self.subscribed_symbols:
            # Group by depth level to send efficiently
            depth_groups = {}
            for code, depth in self.subscribed_symbols.items():
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(code)
            
            for depth, codes in depth_groups.items():
                self._send_subscription(codes, depth)
                
        # Start heartbeat thread (delayed start)
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        time.sleep(5)  # Wait a bit before first heartbeat
        while self.is_connected:
            try:
                seq_id = int(time.time() * 1000) % 2147483647
                payload = {
                    "cmd_id": 22000, # Heartbeat
                    "seq_id": seq_id,
                    "trace": self._get_trace(),
                    "data": {}
                }
                self.ws.send(json.dumps(payload))
                time.sleep(15) # Heartbeat every 15s (server requires < 20s usually)
            except Exception:
                break

    def _on_message(self, ws, message):
        try:
            # logger.info(f"Raw msg: {message[:100]}") 
            data = json.loads(message)
            
            # Store latest tick if it's market data
            if 'data' in data and isinstance(data['data'], dict) and 'code' in data['data']:
                code = data['data']['code']
                self.latest_ticks[code] = data['data']
                # logger.info(f"Updated tick for {code}")
            
            # Dispatch to callbacks
            for cb in self.callbacks:
                cb(data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        logger.error(f"AllTick WS Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("AllTick WS Closed")
        self.is_connected = False
        # Optional: Implement auto-reconnect logic here if needed

# Example usage (for testing):
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TOKEN = "085d4dda8f5195556c0dc5c9ebc7d6ac-c-app"
    client = AllTickClient(TOKEN)
    
    def print_tick(data):
        if 'data' in data and 'code' in data['data']:
             tick = data['data']
             print(f"Tick: {tick['code']} Price: {tick.get('bids', [{}])[0].get('price')} Time: {tick.get('tick_time')}")
        else:
            print("Msg:", data)

    client.add_callback(print_tick)
    client.connect()
    time.sleep(2)
    client.subscribe(["700.HK", "AAPL.US"])
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()
