"""RealityBridge — Dual-mode gatekeeper with promotion threshold."""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional
from nexus_os.relay.mode import RelayMode
from nexus_os.relay.providers_strict import StrictProvider, get_strict_providers
from nexus_os.relay.providers_frontier import FrontierProvider, get_frontier_providers


PROMOTION_THRESHOLD = 0.85


@dataclass
class ProviderTrackRecord:
    provider: str
    successes: int = 0
    failures: int = 0
    samples: int = 0
    first_seen: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.samples, 1)

    @property
    def is_ready_for_promotion(self) -> bool:
        return self.samples >= 10 and self.success_rate >= PROMOTION_THRESHOLD


class RealityBridge:
    def __init__(self, mode: RelayMode = RelayMode.STRICT):
        self._mode = mode
        self._tracks: dict[str, ProviderTrackRecord] = {}

    @property
    def mode(self) -> RelayMode:
        return self._mode

    def set_mode(self, mode: RelayMode):
        self._mode = mode

    def get_providers(self):
        if self._mode == RelayMode.STRICT:
            strict = get_strict_providers()
            promoted = [p.name for p in self._promoted_providers()]
            return strict + [self._as_strict(p) for p in promoted]
        return get_frontier_providers()

    def record_success(self, provider: str):
        if provider not in self._tracks:
            self._tracks[provider] = ProviderTrackRecord(provider=provider, first_seen=time.time())
        self._tracks[provider].successes += 1
        self._tracks[provider].samples += 1

    def record_failure(self, provider: str):
        if provider not in self._tracks:
            self._tracks[provider] = ProviderTrackRecord(provider=provider, first_seen=time.time())
        self._tracks[provider].failures += 1
        self._tracks[provider].samples += 1

    def can_promote(self, provider: str) -> bool:
        track = self._tracks.get(provider)
        if not track:
            return False
        return track.is_ready_for_promotion

    def _promoted_providers(self) -> list[ProviderTrackRecord]:
        return [t for t in self._tracks.values() if t.is_ready_for_promotion]

    def _as_strict(self, track: ProviderTrackRecord) -> StrictProvider:
        return StrictProvider(
            name=track.provider,
            priority=0,
            api_key_env="",
            base_url="http://localhost:11434",
            models=[f"{track.provider}-promoted"],
        )

    def get_track_summary(self) -> dict:
        return {
            "mode": self._mode.value,
            "tracks": {
                k: {"successes": v.successes, "failures": v.failures, "samples": v.samples, "success_rate": v.success_rate, "promotable": v.is_ready_for_promotion}
                for k, v in self._tracks.items()
            },
        }
