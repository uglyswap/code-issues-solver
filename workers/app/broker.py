import dramatiq
from dramatiq.brokers.redis import RedisBroker
from backend.app.config import settings

broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)
