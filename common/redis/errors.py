class RedisConnectionError(Exception):
    def __init__(self):
        self.message = "Failed to connect to Redis"
        super().__init__(self.message)


class RedisSetError(Exception):
    def __init__(self, key: str, value: str):
        self.message = f"Failed to set value {value} in Redis with key {key}"
        super().__init__(self.message)
