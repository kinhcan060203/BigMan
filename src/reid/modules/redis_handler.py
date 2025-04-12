import redis
from redis.exceptions import TimeoutError, ConnectionError
from redis.backoff import ExponentialBackoff
from redis.retry import Retry
from redis.exceptions import RedisError, TimeoutError


class RedisHandler:
    def __init__(self, host="localhost", port=6381, db=0, timeout=5):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            socket_timeout=timeout,
            socket_connect_timeout=timeout,
            retry_on_timeout=True,
            retry=Retry(ExponentialBackoff(cap=10, base=1), 25),
            retry_on_error=[ConnectionError, TimeoutError, ConnectionResetError],
            health_check_interval=1,
        )

    def set(self, key, value, ex=None):
        try:
            self.redis_client.set(key, value, ex=ex)
        except (RedisError, TimeoutError) as e:
            raise e
    def get(self, key):
        try:
            if not self.redis_client.exists(key):
                return None
            return self.redis_client.get(key)
        except (RedisError, TimeoutError) as e:
            raise e
    def rpush(self, key, value):
        try:
            self.redis_client.rpush(key, value)
        except (RedisError, TimeoutError) as e:
            raise e
        
    def delete(self, key):
        try:
            self.redis_client.delete(key)
        except (RedisError, TimeoutError) as e:
            raise e
        
    def lrange(self, key, start, end):
        try:
            return self.redis_client.lrange(key, start, end)
        except (RedisError, TimeoutError) as e:
            raise e