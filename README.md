# ClearToll — an OpenAI-compatible endpoint with published prices

[cleartoll.io](https://cleartoll.io) · [docs](https://cleartoll.io/docs.html) · [get a key](https://cleartoll.io/signup.html)

ClearToll routes each request to the cheapest healthy upstream provider and prints the
arithmetic in every response: what the model costs on the market, what we paid, and the
margin we added. No seat fees, no monthly minimum, credit does not expire.

```bash
curl https://api.cleartoll.io/v1/chat/completions \
  -H "Authorization: Bearer $CLEARTOLL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek/deepseek-v4-flash",
       "messages":[{"role":"user","content":"hello"}]}'
```

## Drop-in for the OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="https://api.cleartoll.io/v1", api_key="sk-ct-...")

r = client.chat.completions.create(
    model="deepseek/deepseek-v4-flash",
    messages=[{"role": "user", "content": "hello"}],
)
print(r.choices[0].message.content)
print(r.model_extra["cleartoll"])   # request_id, charged_usd, upstream_usd, margin, provider
```

```javascript
import OpenAI from "openai";

const client = new OpenAI({ baseURL: "https://api.cleartoll.io/v1", apiKey: process.env.CLEARTOLL_KEY });

const r = await client.chat.completions.create({
  model: "deepseek/deepseek-v4-flash",
  messages: [{ role: "user", content: "hello" }],
});
console.log(r.choices[0].message.content, r.cleartoll);
```

## What the `cleartoll` block tells you

Every non-streaming response carries:

| field | meaning |
|---|---|
| `request_id` | id for `GET /v1/generation?id=...` |
| `provider` | which upstream actually served it |
| `upstream_usd` | what that provider will bill us for these tokens |
| `charged_usd` | what we billed you |
| `margin` | the declared multiplier (0.08 – 0.12) |

If the provider's price times our margin would exceed the market list price, **list wins** —
the cap is enforced in code, so you never pay above the public price for the model.

## Endpoints

`POST /v1/chat/completions` · `GET /v1/models` · `GET /v1/models/{id}/endpoints` ·
`GET /v1/providers` · `GET /v1/credits` · `GET /v1/generation?id=` · `GET /v1/activity[.csv]` ·
`GET /v1/key` · `POST /v1/keys` · `POST /v1/topup` · `POST /v1/decide` · `POST /migrate/analyze`

Streaming follows the OpenAI protocol (`stream: true`, `[DONE]` terminator).

## Decisions without a chat model

`POST /v1/decide` classifies a request against a task definition for $0.002 per decision,
cached repeats are free — cheaper than sending 800 tokens to a 70B model to get one label.

```bash
curl https://api.cleartoll.io/v1/decide \
  -H "Authorization: Bearer $CLEARTOLL_KEY" -H "Content-Type: application/json" \
  -d '{"task":"lead_intent","input":{"message":"how much for 50 chairs?"}}'
```

## Migrating

`POST /migrate/analyze` accepts your OpenRouter activity CSV and returns what the same
tokens would cost here, model by model. Models we do not serve yet are passed through at
your current price, so the number stays conservative.

## Errors and limits

`401` bad key · `402` out of credit or daily budget · `404` unknown model · `429` rate limit ·
`502` upstream failed everywhere · `503` no provider at or below the published price.

Defaults: 120 requests/minute, $20/day per key. Failover across providers is automatic;
a failed request before tokens arrive is not billed.

## This repository

`clients/` contains the two thin wrappers used in the examples. Nothing here needs our
permission to read: the API is documented at [cleartoll.io/docs.html](https://cleartoll.io/docs.html).

MIT.
