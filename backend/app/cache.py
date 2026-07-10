"""Redis cache access for the application service.

A short socket timeout is used deliberately so that when Redis is stopped the
application surfaces the failure quickly (connection refused / timeout) instead
of hanging — this is what produces the observable "redis_outage" symptoms.
"""
import os

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# A single client; redis-py manages a connection pool under the hood.
_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    socket_connect_timeout=1.0,
    socket_timeout=1.0,
    decode_responses=True,
)


def get_client() -> "redis.Redis":
    return _client


def cache_get(key: str):
    return _client.get(key)


def cache_set(key: str, value: str, ttl: int = 30) -> None:
    _client.set(key, value, ex=ttl)
