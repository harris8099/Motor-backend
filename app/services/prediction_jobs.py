import importlib
import json
import logging
from typing import Optional

import numpy as np
from fastapi import BackgroundTasks
from sqlalchemy import text

from app.database import AsyncSessionLocal, settings
from app.schemas import SensorPayload
from app.services.advanced_ml_prediction import run_advanced_ml_predictions
from app.services.ml_prediction import run_ml_predictions
from app.services.prediction import run_predictions

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """Converts numpy values and non-finite floats into JSON-safe values."""

    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            value = float(obj)
            return None if np.isnan(value) or np.isinf(value) else value
        if isinstance(obj, np.ndarray):
            return [sanitize_for_json(item) for item in obj.tolist()]
        return super().default(obj)


def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(value) for value in obj]
    if isinstance(obj, np.ndarray):
        return [sanitize_for_json(value) for value in obj.tolist()]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        value = float(obj)
        return None if np.isnan(value) or np.isinf(value) else value
    if isinstance(obj, float):
        return None if np.isnan(obj) or np.isinf(obj) else obj
    return obj


def _resolve_dispatch_mode() -> str:
    mode = getattr(settings, "prediction_dispatch_mode", "auto").strip().lower()
    redis_url = getattr(settings, "redis_url", "").strip()
    if mode == "auto":
        return "redis" if redis_url else "background"
    if mode not in {"background", "redis"}:
        logger.warning("Unknown prediction dispatch mode '%s'; falling back to background", mode)
        return "background"
    return mode


def _get_redis_module():
    try:
        return importlib.import_module("redis.asyncio")
    except ImportError:
        return None


async def enqueue_prediction_job(
    payload_data: dict,
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """
    Dispatch prediction work either to FastAPI background tasks or a Redis queue.
    Returns the mode actually used.
    """
    mode = _resolve_dispatch_mode()

    if mode == "redis":
        redis_module = _get_redis_module()
        redis_url = getattr(settings, "redis_url", "").strip()
        if redis_module and redis_url:
            client = redis_module.from_url(redis_url, decode_responses=True)
            try:
                await client.rpush(settings.prediction_queue_name, json.dumps(payload_data))
                return "redis"
            except Exception:
                logger.exception("Redis enqueue failed; falling back to in-process background task")
            finally:
                await client.aclose()
        else:
            logger.warning("Redis dispatch requested but redis package or REDIS_URL is unavailable")

    if background_tasks is not None:
        background_tasks.add_task(process_prediction_payload, payload_data)
        return "background"

    await process_prediction_payload(payload_data)
    return "inline"


async def process_prediction_payload(payload_data: dict) -> None:
    """
    Run the prediction pipeline for a payload and persist results.
    Safe to call from the API process or from a dedicated worker.
    """
    payload = SensorPayload.model_validate(payload_data)

    async with AsyncSessionLocal() as db:
        try:
            prediction_mode = getattr(settings, "prediction_mode", "advanced")
            if prediction_mode == "advanced":
                predictions = await run_advanced_ml_predictions(payload, db)
            elif prediction_mode == "ml":
                predictions = await run_ml_predictions(payload, db)
            else:
                predictions = run_predictions(payload)

            for prediction in predictions:
                confidence = sanitize_for_json(prediction["confidence"])
                details = sanitize_for_json(prediction["details"]) if prediction["details"] else {}

                await db.execute(
                    text(
                        """
                        INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
                        VALUES (:device_id, :type, :confidence, :severity, :details)
                        """
                    ),
                    {
                        "device_id": payload.deviceId,
                        "type": prediction["type"],
                        "confidence": confidence,
                        "severity": prediction["severity"],
                        "details": json.dumps(details, cls=NumpyEncoder),
                    },
                )

            await db.execute(
                text(
                    """
                    DELETE FROM predictions
                    WHERE device_id = :device_id
                      AND ts < NOW() - INTERVAL '7 days'
                    """
                ),
                {"device_id": payload.deviceId},
            )

            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Prediction pipeline failed for device %s", payload.deviceId)
            raise
