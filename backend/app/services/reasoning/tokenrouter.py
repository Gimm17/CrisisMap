from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import get_settings
from app.models.schemas import AssessmentReport, BuildingDamage, TokenRouterMetadata
from app.services.reasoning.fallback import build_fallback_report
from app.services.reasoning.prompt_builder import build_reasoning_messages

logger = logging.getLogger(__name__)


class TokenRouterReasoner:
    def __init__(self, model: str | None = None) -> None:
        self.settings = get_settings()
        self.model = model or self.settings.tokenrouter_model

    async def generate_report(self, buildings: list[BuildingDamage], humanitarian_layers: dict[str, Any]) -> AssessmentReport:
        if not self.settings.tokenrouter_api_key:
            return build_fallback_report(buildings)

        started = time.perf_counter()
        metadata = TokenRouterMetadata(
            provider="tokenrouter",
            model=self.model,
            routing_mode="auto" if self.model.startswith("auto:") else "direct",
        )
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.settings.tokenrouter_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.tokenrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": build_reasoning_messages(buildings, humanitarian_layers),
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                metadata.latency_ms = int((time.perf_counter() - started) * 1000)
                metadata.x_request_id = response.headers.get("x-request-id")
                response.raise_for_status()
                payload = response.json()
                metadata.provider = payload.get("provider", metadata.provider)
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                parsed["tokenrouter"] = metadata.model_dump()
                return AssessmentReport.model_validate(parsed)
        except Exception as exc:
            metadata.latency_ms = int((time.perf_counter() - started) * 1000)
            metadata.provider = "heuristic-fallback"
            metadata.model = "local-heuristic"
            metadata.routing_mode = "offline"
            logger.warning("TokenRouter reasoning failed, using fallback: %s", exc)
            return build_fallback_report(buildings, metadata)
