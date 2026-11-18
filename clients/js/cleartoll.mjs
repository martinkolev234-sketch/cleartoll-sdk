/**
 * cleartoll — минимален клиент за ClearToll (OpenAI-съвместим), без зависимости.
 *
 *   const ct = new ClearToll(process.env.CLEARTOLL_KEY);
 *   console.log(await ct.chat("deepseek/deepseek-v4-flash", "здравей"));
 *   for await (const t of ct.stream("openai/gpt-oss-120b", [{role:"user",content:"hi"}])) process.stdout.write(t);
 *
 * Всяка заявка носи блок `cleartoll` (request_id, provider, upstream_usd, charged_usd);
 * тук той е първокласен, вместо да се губи в model_extra.
 */
const DEFAULT_BASE = "https://api.cleartoll.io/v1";

export class ClearTollError extends Error {
  constructor(status, detail) {
    super(`HTTP ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export class ClearToll {
  constructor(apiKey = process.env.CLEARTOLL_KEY, baseUrl = DEFAULT_BASE) {
    if (!apiKey) throw new Error("нужен е ключ: CLEARTOLL_KEY=sk-ct-...");
    this.key = apiKey;
    this.base = baseUrl.replace(/\/$/, "");
  }

  async #call(method, path, body) {
    const r = await fetch(this.base + path, {
      method,
      headers: {
        Authorization: `Bearer ${this.key}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) {
      let detail = await r.text();
      try { detail = JSON.parse(detail).detail ?? detail; } catch {}
      throw new ClearTollError(r.status, String(detail).slice(0, 300));
    }
    return r.json();
  }

  async models({ onlyServable = true, ...filters } = {}) {
    const q = new URLSearchParams({ only_servable: onlyServable ? 1 : 0, limit: 0, ...filters });
    return (await this.#call("GET", `/models?${q}`)).data;
  }

  async chat(model, prompt, { system, maxTokens = 512, temperature = 0.7, ...extra } = {}) {
    const messages = [
      ...(system ? [{ role: "system", content: system }] : []),
      { role: "user", content: prompt },
    ];
    const d = await this.chatRaw(model, messages, { maxTokens, temperature, ...extra });
    return d.choices[0].message.content;
  }

  async chatRaw(model, messages, { maxTokens = 512, temperature = 0.7, ...extra } = {}) {
    return this.#call("POST", "/chat/completions", {
      model, messages, max_tokens: maxTokens, temperature, ...extra,
    });
  }

  async *stream(model, messages, extra = {}) {
    const r = await fetch(this.base + "/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${this.key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, stream: true, ...extra }),
    });
    if (!r.ok) throw new ClearTollError(r.status, (await r.text()).slice(0, 300));
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;
        try {
          const chunk = JSON.parse(payload);
          const piece = chunk.choices?.[0]?.delta?.content;
          if (piece) yield piece;
        } catch { /* частичен ред — остава в буфера */ }
      }
    }
  }

  decide(task, input, explain = false) {
    return this.#call("POST", "/decide", { task, input, explain });
  }

  async credits() {
    return (await this.#call("GET", "/credits")).data;
  }
}

export default ClearToll;
