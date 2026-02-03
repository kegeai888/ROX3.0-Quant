import redis.asyncio as redis
import json
import logging
import os
import asyncio
from typing import Callable, Awaitable, Dict, List

logger = logging.getLogger(__name__)

class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.redis = None
            cls._instance.pubsub = None
            cls._instance.handlers: Dict[str, List[Callable]] = {}
            cls._instance.is_listening = False
        return cls._instance

    async def connect(self):
        if not self.redis:
            redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                await self.redis.ping()
                logger.info(f"EventBus connected to Redis at {redis_url}")
            except Exception as e:
                logger.error(f"EventBus connection failed: {e}")
                self.redis = None

    async def publish(self, channel: str, message: dict):
        if not self.redis:
            await self.connect()
        if self.redis:
            try:
                await self.redis.publish(channel, json.dumps(message))
            except Exception as e:
                logger.error(f"Publish failed: {e}")

    def subscribe(self, channel: str, callback: Callable[[dict], Awaitable[None]]):
        if channel not in self.handlers:
            self.handlers[channel] = []
        self.handlers[channel].append(callback)
        logger.info(f"EventBus: Registered handler for '{channel}'")

    async def start_listening(self):
        if self.is_listening:
            return
        
        await self.connect()
        if not self.redis:
            logger.warning("Redis not available, EventBus listener disabled.")
            return

        self.pubsub = self.redis.pubsub()
        self.is_listening = True
        
        # Subscribe to all registered channels
        if self.handlers:
            await self.pubsub.subscribe(*self.handlers.keys())
            logger.info(f"EventBus listening on channels: {list(self.handlers.keys())}")

        asyncio.create_task(self._listener_loop())

    async def _listener_loop(self):
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data_str = message['data']
                    try:
                        data = json.loads(data_str)
                        if channel in self.handlers:
                            for handler in self.handlers[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(data)
                                    else:
                                        handler(data)
                                except Exception as e:
                                    logger.error(f"Handler error on {channel}: {e}")
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"EventBus listener crashed: {e}")
            self.is_listening = False
