import redis


class RedisMonitor:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.redis_client = redis.Redis(host=self.host, port=self.port)

    def get_keys(self, pattern):
        keys = self.redis_client.keys(pattern)
        return keys

    def get_value(self, key):
        value = self.redis_client.get(key)
        return value

    def set_value(self, key, value):
        self.redis_client.set(key, value)

    def delete_key(self, key):
        self.redis_client.delete(key)

    def disconnect(self):
        self.redis_client.close()
