"""cleartoll — най-малкият клиент за ClearToll (OpenAI-съвместим).

    pip install requests
    export CLEARTOLL_KEY=sk-ct-...
    python - <<'EOF'
    from cleartoll import ClearToll
    ct = ClearToll()
    print(ct.chat("deepseek/deepseek-v4-flash", "здравей"))
    print(ct.credits())
    EOF

Защо съществува: openai-python работи с нашия endpoint, но хвърля полетата на
`cleartoll` блока (цена, доставчик, марж) в model_extra. Тук са първокласни.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, List, Optional

import requests

DEFAULT_BASE = "https://api.cleartoll.io/v1"


class ClearTollError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__("HTTP %d: %s" % (status, detail))
        self.status = status
        self.detail = detail


class ClearToll:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE, timeout: int = 120):
        self.key = api_key or os.environ.get("CLEARTOLL_KEY", "")
        if not self.key:
            raise SystemExit("нужен е ключ: export CLEARTOLL_KEY=sk-ct-... (или ClearToll(api_key=...))")
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self._s = requests.Session()
        self._s.headers.update({"Authorization": "Bearer " + self.key,
                                "Content-Type": "application/json"})

    # ---------------------------------------------------------------- помощни
    def _call(self, method: str, path: str, **kw) -> Dict[str, Any]:
        r = self._s.request(method, self.base + path, timeout=self.timeout, **kw)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise ClearTollError(r.status_code, str(detail)[:300])
        return r.json()

    # ---------------------------------------------------------------- API
    def models(self, only_servable: bool = True, **filters) -> List[Dict[str, Any]]:
        q = {"only_servable": int(only_servable), "limit": 0, **filters}
        return self._call("GET", "/models", params=q)["data"]

    def chat(self, model: str, prompt: str, *, system: Optional[str] = None,
             max_tokens: int = 512, temperature: float = 0.7, **extra) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        return self.chat_messages(model, msgs, max_tokens=max_tokens, temperature=temperature, **extra)

    def chat_messages(self, model: str, messages: List[Dict[str, str]], *,
                      max_tokens: int = 512, temperature: float = 0.7, **extra) -> str:
        d = self.chat_raw(model, messages, max_tokens=max_tokens, temperature=temperature, **extra)
        return d["choices"][0]["message"]["content"]

    def chat_raw(self, model: str, messages: List[Dict[str, str]], *,
                 max_tokens: int = 512, temperature: float = 0.7, **extra) -> Dict[str, Any]:
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "temperature": temperature, **extra}
        return self._call("POST", "/chat/completions", data=json.dumps(body))

    def stream(self, model: str, messages: List[Dict[str, str]], **extra) -> Iterator[str]:
        """Връща парчета текст, докато пристигат. Таксува се и прекъснат стрийм."""
        body = {"model": model, "messages": messages, "stream": True, **extra}
        with self._s.post(self.base + "/chat/completions", data=json.dumps(body),
                          stream=True, timeout=self.timeout) as r:
            if r.status_code >= 400:
                raise ClearTollError(r.status_code, r.text[:300])
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except ValueError:
                    continue
                for ch in chunk.get("choices") or []:
                    piece = (ch.get("delta") or {}).get("content")
                    if piece:
                        yield piece

    def decide(self, task: str, payload: Dict[str, Any], explain: bool = False) -> Dict[str, Any]:
        return self._call("POST", "/decide",
                          data=json.dumps({"task": task, "input": payload, "explain": explain}))

    def credits(self) -> Dict[str, Any]:
        return self._call("GET", "/credits")["data"]

    def generation(self, request_id: str) -> Dict[str, Any]:
        return self._call("GET", "/generation", params={"id": request_id})["data"]

    def topup(self, pack: str = "10") -> str:
        """Връща URL на Stripe Checkout. Кредитите влизат след плащане."""
        return self._call("POST", "/topup", data=json.dumps({"pack": pack}))["url"]
