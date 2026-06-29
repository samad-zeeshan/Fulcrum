from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(frozen=True)
class DeepSeekConfig:

    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"

    thinking: bool = False
    thinking_off_extra_body: dict = field(default_factory=lambda: {"thinking": {"type": "disabled"}})

    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_s: float = 60.0
    max_retries: int = 2

PRICING = {
    "deepseek-v4-flash": {
        "prompt_cache_miss": 0.14 / 1_000_000,
        "prompt_cache_hit": 0.014 / 1_000_000,
        "completion": 0.28 / 1_000_000,
    },
}

def price_for(model: str) -> dict:
    return PRICING.get(model, PRICING["deepseek-v4-flash"])
