# cleartoll (Python)

```bash
pip install requests
export CLEARTOLL_KEY=sk-ct-...
```

```python
from cleartoll import ClearToll

ct = ClearToll()
print(ct.chat("deepseek/deepseek-v4-flash", "hello"))

raw = ct.chat_raw("openai/gpt-oss-120b", [{"role": "user", "content": "hi"}], max_tokens=8)
print(raw["cleartoll"])        # request_id, provider, upstream_usd, charged_usd, margin

for piece in ct.stream("deepseek/deepseek-v4-flash", [{"role": "user", "content": "count 1 2 3"}]):
    print(piece, end="", flush=True)

print(ct.decide("lead_intent", {"message": "how much for 50 chairs?"}))
print(ct.credits())            # {"total_credits": 0.5, "total_usage": 0.0}
```
