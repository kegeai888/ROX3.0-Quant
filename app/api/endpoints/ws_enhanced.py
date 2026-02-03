from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import List, Dict, Any
import redis.asyncio as redis
from datetime import datetime
import os
from app.db import get_market_rankings, get_north_fund

logger = logging.getLogger("rox-ws")
router = APIRouter()

class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriber_connections: Dict[str, List[WebSocket]] = {}
        self.background_tasks: List[asyncio.Task] = []
        self.redis_client = None
        self.pubsub = None
        
    async def init_redis(self):
        """Initialize Redis connection for pub/sub"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to market data channels
            await self.pubsub.subscribe("market_data", "alerts", "trades")
            logger.info("Redis pub/sub initialized successfully")
            
            # Start Redis message consumer
            task = asyncio.create_task(self._redis_message_consumer())
            self.background_tasks.append(task)
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Fallback to broadcast mode without Redis
    
    async def _redis_message_consumer(self):
        """Consume messages from Redis pub/sub"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    # Broadcast to relevant subscribers
                    if channel in self.subscriber_connections:
                        await self._broadcast_to_channel(channel, data)
                    
                    # Also broadcast to all active connections
                    await self.send_json(data)
                    
        except Exception as e:
            logger.error(f"Redis message consumer error: {e}")
    
    async def connect(self, websocket: WebSocket, subscriptions: List[str] = None):
        """Accept new WebSocket connection with optional subscriptions"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Add to subscriber lists if specified
        if subscriptions:
            for channel in subscriptions:
                if channel not in self.subscriber_connections:
                    self.subscriber_connections[channel] = []
                self.subscriber_connections[channel].append(websocket)
        
        # Send welcome message
        welcome_msg = {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "subscriptions": subscriptions or []
        }
        await websocket.send_json(welcome_msg)
        
        logger.info(f"WS Connected. Active: {len(self.active_connections)}")
        
        # Initialize Redis if not already done
        if not self.redis_client:
            await self.init_redis()
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from subscriber lists
            for channel in list(self.subscriber_connections.keys()):
                if websocket in self.subscriber_connections[channel]:
                    self.subscriber_connections[channel].remove(websocket)
                    if not self.subscriber_connections[channel]:
                        del self.subscriber_connections[channel]
        
        logger.info(f"WS Disconnected. Active: {len(self.active_connections)}")
        
        # Cleanup if no connections left
        if len(self.active_connections) == 0:
            self._cleanup_tasks()
    
    async def _broadcast_to_channel(self, channel: str, data: Dict[str, Any]):
        """Broadcast message to specific channel subscribers"""
        if channel in self.subscriber_connections:
            dead_connections = []
            for connection in self.subscriber_connections[channel]:
                try:
                    await connection.send_json(data)
                except Exception:
                    dead_connections.append(connection)
            
            # Cleanup dead connections
            for dead_conn in dead_connections:
                self.disconnect(dead_conn)
    
    async def publish_to_redis(self, channel: str, data: Dict[str, Any]):
        """Publish message to Redis channel"""
        if self.redis_client:
            try:
                await self.redis_client.publish(channel, json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")
    
    async def send_json(self, message: Dict[str, Any], filter_func=None):
        """Send JSON message to connections, optionally filtered"""
        if filter_func:
            target_connections = [conn for conn in self.active_connections if filter_func(conn)]
        else:
            target_connections = self.active_connections
        
        dead_connections = []
        for connection in target_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Cleanup dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
    
    def _cleanup_tasks(self):
        """Cancel all background tasks"""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        self.background_tasks.clear()
        
        # Close Redis connections
        if self.pubsub:
            asyncio.create_task(self.pubsub.close())
        if self.redis_client:
            asyncio.create_task(self.redis_client.close())

# Enhanced market data broadcaster
class MarketDataBroadcaster:
    def __init__(self, manager: EnhancedConnectionManager):
        self.manager = manager
        self.is_running = False
        self.update_interval = 3  # seconds
        
    async def start(self):
        """Start market data broadcasting"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting enhanced market data broadcasting")
        
        # Start multiple data streams
        tasks = [
            asyncio.create_task(self._broadcast_market_indices()),
            asyncio.create_task(self._broadcast_stock_updates()),
            asyncio.create_task(self._broadcast_sector_rotation()),
            asyncio.create_task(self._broadcast_alerts()),
            asyncio.create_task(self._broadcast_market_rankings()),
            asyncio.create_task(self._broadcast_hsgt()),
            asyncio.create_task(self._broadcast_sentiment()),
        ]
        
        self.manager.background_tasks.extend(tasks)
    
    async def stop(self):
        """Stop market data broadcasting"""
        self.is_running = False
        logger.info("Stopping market data broadcasting")
    
    async def _broadcast_market_indices(self):
        """Broadcast major market indices"""
        try:
            while self.is_running:
                # Fetch real market data from external API or database
                market_data = await self._fetch_market_indices()
                
                message = {
                    "type": "market_indices",
                    "timestamp": datetime.now().isoformat(),
                    "data": market_data
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            logger.info("Market indices broadcasting stopped")
        except Exception as e:
            logger.error(f"Market indices broadcasting error: {e}")
    
    async def _broadcast_stock_updates(self):
        """Broadcast individual stock updates"""
        try:
            while self.is_running:
                # Fetch stock updates for watched stocks
                stock_updates = await self._fetch_stock_updates()
                
                message = {
                    "type": "stock_updates",
                    "timestamp": datetime.now().isoformat(),
                    "data": stock_updates
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(5)  # Less frequent updates
                
        except asyncio.CancelledError:
            logger.info("Stock updates broadcasting stopped")
        except Exception as e:
            logger.error(f"Stock updates broadcasting error: {e}")
    
    async def _broadcast_sector_rotation(self):
        """Broadcast sector rotation and flow data"""
        try:
            while self.is_running:
                sector_data = await self._fetch_sector_data()
                
                message = {
                    "type": "sector_rotation",
                    "timestamp": datetime.now().isoformat(),
                    "data": sector_data
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(10)  # Even less frequent
                
        except asyncio.CancelledError:
            logger.info("Sector rotation broadcasting stopped")
        except Exception as e:
            logger.error(f"Sector rotation broadcasting error: {e}")

    async def _broadcast_market_rankings(self):
        """Broadcast market rankings (Top Sectors, Stocks, Flows)"""
        try:
            while self.is_running:
                # Use real data from db.py
                rankings = await get_market_rankings()
                
                # Mock money flow if not present
                north_money = 0
                main_money = 0
                
                # Try to get real north money
                hsgt = await get_north_fund()
                if hsgt:
                    for item in hsgt:
                        if item['资金方向'] == '北向':
                            north_money = item['成交净买额']
                
                # Mock main money based on time
                main_money = (hash(datetime.now().isoformat()) % 2000000000) - 1000000000
                
                data = {
                    "sectors": rankings.get("sectors", []),
                    "stocks": rankings.get("stocks", []),
                    "north_money": f"{north_money/100000000:.2f}亿",
                    "main_money": f"{main_money/100000000:.2f}亿"
                }
                
                message = {
                    "type": "market_data",
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("Market rankings broadcasting stopped")
        except Exception as e:
            logger.error(f"Market rankings broadcasting error: {e}")

    async def _broadcast_hsgt(self):
        """Broadcast HSGT (North/South) data"""
        try:
            while self.is_running:
                # Construct chart data
                # In a real app, we'd query historical data. Here we simulate a day's curve.
                now = datetime.now()
                hours = [f"{h:02d}:00" for h in range(9, 16)]
                
                north_data = []
                south_data = []
                
                base_north = 0
                base_south = 0
                
                for h in hours:
                    base_north += (hash(h + "north") % 100000000) - 30000000
                    base_south += (hash(h + "south") % 100000000) - 20000000
                    north_data.append({"time": f"{now.strftime('%Y-%m-%d')} {h}", "value": base_north})
                    south_data.append({"time": f"{now.strftime('%Y-%m-%d')} {h}", "value": base_south})
                
                data = {
                    "north": north_data,
                    "south": south_data
                }
                
                message = {
                    "type": "hsgt_data",
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(10)
                
        except asyncio.CancelledError:
            logger.info("HSGT broadcasting stopped")
        except Exception as e:
            logger.error(f"HSGT broadcasting error: {e}")

    async def _broadcast_sentiment(self):
        """Broadcast sentiment data"""
        try:
            while self.is_running:
                # Mock sentiment data
                data = {
                    "retail_dist": {
                        "super": 15 + (hash(datetime.now().isoformat()) % 5),
                        "big": 25 + (hash(datetime.now().isoformat()) % 5),
                        "mid": 30 + (hash(datetime.now().isoformat()) % 5),
                        "small": 30 + (hash(datetime.now().isoformat()) % 5)
                    },
                    "bull_bear": {
                        "score": 45 + (hash(datetime.now().isoformat()) % 20),
                        "trend": "neutral"
                    }
                }
                
                message = {
                    "type": "sentiment_data",
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                
                await self.manager.send_json(message)
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("Sentiment broadcasting stopped")
        except Exception as e:
            logger.error(f"Sentiment broadcasting error: {e}")
    
    async def _broadcast_alerts(self):
        """Broadcast trading alerts and notifications"""
        try:
            while self.is_running:
                # Check for alerts every 30 seconds
                alerts = await self._check_alerts()
                
                if alerts:
                    message = {
                        "type": "trading_alerts",
                        "timestamp": datetime.now().isoformat(),
                        "alerts": alerts
                    }
                    
                    # Publish to Redis for persistence
                    await self.manager.publish_to_redis("alerts", message)
                    
                    # Also broadcast directly
                    await self.manager.send_json(message)
                
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Alerts broadcasting stopped")
        except Exception as e:
            logger.error(f"Alerts broadcasting error: {e}")
    
    async def _fetch_market_indices(self) -> Dict[str, Any]:
        """Fetch market indices data"""
        # In production, this would fetch from external API or database
        # For now, return simulated data
        return {
            "sh000001": {
                "name": "上证指数",
                "price": 3200 + (hash(datetime.now().isoformat()) % 100 - 50),
                "change": round((hash(datetime.now().isoformat()) % 1000 - 500) / 100, 2),
                "change_percent": round((hash(datetime.now().isoformat()) % 200 - 100) / 100, 2)
            },
            "sz399001": {
                "name": "深证成指",
                "price": 12000 + (hash(datetime.now().isoformat()) % 200 - 100),
                "change": round((hash(datetime.now().isoformat()) % 2000 - 1000) / 100, 2),
                "change_percent": round((hash(datetime.now().isoformat()) % 300 - 150) / 100, 2)
            },
            "sz399006": {
                "name": "创业板指",
                "price": 2500 + (hash(datetime.now().isoformat()) % 80 - 40),
                "change": round((hash(datetime.now().isoformat()) % 800 - 400) / 100, 2),
                "change_percent": round((hash(datetime.now().isoformat()) % 400 - 200) / 100, 2)
            }
        }
    
    async def _fetch_stock_updates(self) -> List[Dict[str, Any]]:
        """Fetch stock updates"""
        # Simulate stock data
        stocks = ["000001", "000002", "600036", "600519"]
        updates = []
        
        for symbol in stocks:
            base_price = 10 + hash(symbol) % 50
            updates.append({
                "symbol": symbol,
                "price": base_price + (hash(datetime.now().isoformat() + symbol) % 10 - 5),
                "change": round((hash(datetime.now().isoformat() + symbol) % 200 - 100) / 100, 2),
                "volume": hash(datetime.now().isoformat() + symbol) % 1000000
            })
        
        return updates
    
    async def _fetch_sector_data(self) -> Dict[str, Any]:
        """Fetch sector rotation data"""
        sectors = ["银行", "房地产", "科技", "消费", "医药"]
        sector_data = {}
        
        for sector in sectors:
            sector_data[sector] = {
                "flow": hash(datetime.now().isoformat() + sector) % 100000000,
                "change_percent": round((hash(datetime.now().isoformat() + sector) % 400 - 200) / 100, 2),
                "main_stocks": [f"{i:06d}" for i in range(1, 6)]
            }
        
        return sector_data
    
    async def _check_alerts(self) -> List[Dict[str, Any]]:
        """Check for trading alerts"""
        alerts = []
        
        # Simulate various alert conditions
        if hash(datetime.now().isoformat()) % 100 < 10:  # 10% chance
            alerts.append({
                "id": f"alert_{hash(datetime.now().isoformat()) % 10000}",
                "type": "price_alert",
                "title": "价格异动提醒",
                "message": "检测到异常价格波动，建议关注相关股票。",
                "severity": "medium",
                "symbols": ["000001", "600036"]
            })
        
        if hash(datetime.now().isoformat()) % 100 < 5:  # 5% chance
            alerts.append({
                "id": f"alert_{hash(datetime.now().isoformat()) % 10000}",
                "type": "volume_alert",
                "title": "成交量异常",
                "message": "某只股票成交量异常放大，可能存在重大消息。",
                "severity": "high",
                "symbols": ["600519"]
            })
        
        return alerts

# Initialize enhanced manager
enhanced_manager = EnhancedConnectionManager()
market_broadcaster = MarketDataBroadcaster(enhanced_manager)

@router.websocket("/ws/enhanced")
async def enhanced_websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint with subscription support"""
    await enhanced_manager.connect(websocket)
    
    # Start market data broadcasting if not already running
    if not market_broadcaster.is_running:
        await market_broadcaster.start()
    
    try:
        while True:
            # Receive and process client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await _handle_client_message(websocket, message)
            except json.JSONDecodeError:
                # Send error response
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format"
                }
                await websocket.send_json(error_response)
                
    except WebSocketDisconnect:
        enhanced_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Enhanced WS Error: {e}")
        enhanced_manager.disconnect(websocket)

async def _handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming client messages"""
    msg_type = message.get("type")
    
    if msg_type == "subscribe":
        # Handle subscription requests
        channels = message.get("channels", [])
        for channel in channels:
            if channel not in enhanced_manager.subscriber_connections:
                enhanced_manager.subscriber_connections[channel] = []
            if websocket not in enhanced_manager.subscriber_connections[channel]:
                enhanced_manager.subscriber_connections[channel].append(websocket)
        
        response = {
            "type": "subscription_confirmed",
            "channels": channels
        }
        await websocket.send_json(response)
        
    elif msg_type == "unsubscribe":
        # Handle unsubscription requests
        channels = message.get("channels", [])
        for channel in channels:
            if (channel in enhanced_manager.subscriber_connections and 
                websocket in enhanced_manager.subscriber_connections[channel]):
                enhanced_manager.subscriber_connections[channel].remove(websocket)
                if not enhanced_manager.subscriber_connections[channel]:
                    del enhanced_manager.subscriber_connections[channel]
        
        response = {
            "type": "unsubscription_confirmed",
            "channels": channels
        }
        await websocket.send_json(response)
        
    elif msg_type == "ping":
        # Handle ping messages
        response = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(response)
        
    elif msg_type == "get_market_data":
        # Handle market data requests
        market_data = await market_broadcaster._fetch_market_indices()
        response = {
            "type": "market_data_response",
            "data": market_data
        }
        await websocket.send_json(response)
        
    else:
        # Unknown message type
        response = {
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        }
        await websocket.send_json(response)

# Legacy endpoint for backward compatibility
@router.websocket("/ws/market")
async def legacy_websocket_endpoint(websocket: WebSocket):
    """Legacy WebSocket endpoint for backward compatibility"""
    await enhanced_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Simple echo for legacy clients
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        enhanced_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Legacy WS Error: {e}")
        enhanced_manager.disconnect(websocket)