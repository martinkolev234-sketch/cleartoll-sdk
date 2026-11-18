# cleartoll (JavaScript, no dependencies)

```bash
npm i -g nothing        # nothing to install: it is one file of fetch()
export CLEARTOLL_KEY=sk-ct-...
```

```js
import { ClearToll } from "./cleartoll.mjs";

const ct = new ClearToll();
console.log(await ct.chat("deepseek/deepseek-v4-flash", "hello"));

for await (const piece of ct.stream("deepseek/deepseek-v4-flash", [
  { role: "user", content: "count 1 2 3" },
])) process.stdout.write(piece);

console.log(await ct.credits());
```
