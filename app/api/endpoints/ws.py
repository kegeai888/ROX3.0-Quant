from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
import aiohttp
from typing import List

logger = logging.getLogger("rox-ws")
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.background_task = None
        # Cache for last known state
        self.last_data = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS Connected. Active: {len(self.active_connections)}")
        
        # Send last known data immediately if available
        if self.last_data:
            await websocket.send_json(self.last_data)
            
        if not self.background_task:
            self.background_task = asyncio.create_task(self.broadcast_market_data())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if len(self.active_connections) == 0 and self.background_task:
            self.background_task.cancel()
            self.background_task = None

    async def fetch_sina_market_data(self):
        """Fetch REAL market data from Sina Finance"""
        # sh000001: 上证指数, sz399001: 深证成指, sz399006: 创业板指
        url = "http://hq.sinajs.cn/list=sh000001,sz399001,sz399006"
        headers = {"Referer": "http://finance.sina.com.cn/"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    return self._parse_sina_data(text)
        except Exception as e:
            logger.error(f"Sina Fetch Error: {e}")
            return None

    def _parse_sina_data(self, text):
        """Parse Sina HQ format"""
        # var hq_str_sh000001="上证指数,3369.12,3360.00,3367.98,...";
        indices = {}
        mapping = {"sh000001": "sh", "sz399001": "sz", "sz399006": "cy"}
        
        lines = text.strip().split('\n')
        for line in lines:
            if not line: continue
            # Extract code and data
            try:
                code_part = line.split('=')[0].split('_str_')[1] # sh000001
                key = mapping.get(code_part)
                if not key: continue
                
                data_part = line.split('"')[1]
                parts = data_part.split(',')
                
                if len(parts) > 3:
                    current_price = float(parts[3])
                    pre_close = float(parts[2])
                    
                    if pre_close == 0: 
                        pct = 0.0
                    else:
                        pct = ((current_price - pre_close) / pre_close) * 100
                    
                    indices[key] = {
                        "price": round(current_price, 2),
                        "pct": round(pct, 2)
                    }
            except Exception:
                continue
                
        if not indices: return None
        return indices

    async def broadcast_market_data(self):
        logger.info("Starting WS Broadcast Loop (Real Market Data)")
        try:
            while True:
                if not self.active_connections:
                    await asyncio.sleep(1)
                    continue

                # Fetch Real Data
                indices_data = await self.fetch_sina_market_data()
                
                if indices_data:
                    data = {
                        "type": "market_tick",
                        "indices": indices_data,
                        "alerts": []
                    }
                    self.last_data = data
                    await self.send_json(data)
                else:
                    import time
                    await self.send_json({"type": "ping", "ts": int(time.time())})

                # Poll every 3 seconds to respect rate limits
                await asyncio.sleep(3) 
        except asyncio.CancelledError:
            logger.info("WS Broadcast Stopped")

    async def send_json(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket)
