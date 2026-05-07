import asyncio
import json
import logging

from app.database import settings
from app.services.prediction_jobs import process_prediction_payload

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    redis_url = getattr(settings, "redis_url", "").strip()
    if not redis_url:
        raise RuntimeError("REDIS_URL must be set to run the prediction worker")

    try:
        import redis.asyncio as redis
    except ImportError as exc:
        raise RuntimeError("redis package is required to run the prediction worker") from exc

    client = redis.from_url(redis_url, decode_responses=True)
    queue_name = settings.prediction_queue_name
    block_seconds = max(int(settings.prediction_worker_block_seconds), 1)

    logger.info("Prediction worker listening on Redis queue '%s'", queue_name)

    try:
        while True:
            message = await client.blpop(queue_name, timeout=block_seconds)
            if not message:
                continue

            _, payload_json = message
            try:
                payload_data = json.loads(payload_json)
                await process_prediction_payload(payload_data)
            except Exception:
                logger.exception("Prediction worker failed while processing a queued job")
    finally:
        await client.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
