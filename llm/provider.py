"""
LLM provider abstraction: a real DeepSeek client and an offline stub.

The stub is deterministic so the eval harness and tests run with no API key.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .config import DeepSeekConfig, price_for

# Minimal .env reader so a local key works without an extra dependency.
def load_dotenv(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)

@dataclass
class Usage:
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        return self.prompt_cache_hit_tokens + self.prompt_cache_miss_tokens

    # Cost is measured from real usage, with cache hits priced below misses.
    def cost(self, model: str) -> float:
        p = price_for(model)
        return (self.prompt_cache_hit_tokens * p["prompt_cache_hit"]
                + self.prompt_cache_miss_tokens * p["prompt_cache_miss"]
                + self.completion_tokens * p["completion"])

    @property
    def cache_hit_rate(self) -> float:
        return self.prompt_cache_hit_tokens / self.prompt_tokens if self.prompt_tokens else 0.0

@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Usage
    latency_s: float
    cost_usd: float
    raw: dict = field(default_factory=dict)

class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str) -> LLMResponse: ...

class DeepSeekProvider:
    name = "deepseek"

    def __init__(self, cfg: DeepSeekConfig | None = None, api_key: str | None = None):
        self.cfg = cfg or DeepSeekConfig()
        self.model = self.cfg.model
        if not (api_key or os.environ.get(self.cfg.api_key_env)):
            load_dotenv()
        key = api_key or os.environ.get(self.cfg.api_key_env)
        if not key:
            raise RuntimeError(
                f"{self.cfg.api_key_env} not set. Export your DeepSeek key, e.g.\n"
                f"  export {self.cfg.api_key_env}=sk-...   (or put it in a .env you source)"
            )
        from openai import OpenAI
        self._client = OpenAI(base_url=self.cfg.base_url, api_key=key,
                              timeout=self.cfg.timeout_s, max_retries=self.cfg.max_retries)

    def complete(self, system: str, user: str) -> LLMResponse:
        # Thinking is off for routine calls to keep latency and cost down.
        extra = {} if self.cfg.thinking else dict(self.cfg.thinking_off_extra_body)
        t0 = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            extra_body=extra or None,
        )
        latency = time.perf_counter() - t0
        u = resp.usage
        # Read the cache hit/miss token split, falling back when a field is absent.
        usage = Usage(
            prompt_cache_hit_tokens=int(getattr(u, "prompt_cache_hit_tokens", 0) or 0),
            prompt_cache_miss_tokens=int(getattr(u, "prompt_cache_miss_tokens",
                                                 getattr(u, "prompt_tokens", 0)) or 0),
            completion_tokens=int(getattr(u, "completion_tokens", 0) or 0),
        )
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, model=self.model, usage=usage, latency_s=latency,
                           cost_usd=usage.cost(self.model),
                           raw={"id": getattr(resp, "id", None)})

# Offline provider for tests and stub eval runs. No network and zero cost.
class StubProvider:

    name = "stub"

    def __init__(self, model: str = "stub-1", responder=None, fixed_text: str | None = None):
        self.model = model
        self._responder = responder
        self._fixed = fixed_text

    def complete(self, system: str, user: str) -> LLMResponse:
        t0 = time.perf_counter()
        if self._responder is not None:
            text = self._responder(system, user)
        elif self._fixed is not None:
            text = self._fixed
        else:
            text = self._echo(user)
        latency = time.perf_counter() - t0

        usage = Usage(
            prompt_cache_hit_tokens=0,
            prompt_cache_miss_tokens=max(1, len(system) + len(user)) // 4,
            completion_tokens=max(1, len(text)) // 4,
        )
        return LLMResponse(text=text, model=self.model, usage=usage, latency_s=latency,
                           cost_usd=0.0, raw={"stub": True})

    @staticmethod
    def _echo(user: str) -> str:
        h = hashlib.sha1(user.encode()).hexdigest()[:8]

        first_ctx = next((ln for ln in user.splitlines() if ln.strip().startswith("[")), "")
        return f"[stub:{h}] {first_ctx}".strip()

# Real DeepSeek if a key is present, otherwise the offline stub.
def get_default_provider(prefer_real: bool = True, **kw) -> LLMProvider:
    env = DeepSeekConfig().api_key_env
    if prefer_real and not os.environ.get(env):
        load_dotenv()
    if prefer_real and os.environ.get(env):
        return DeepSeekProvider(**kw)
    return StubProvider()
