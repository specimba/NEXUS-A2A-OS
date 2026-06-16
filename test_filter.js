import { MODELS, sources, canonicalizeModelId } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/sources.js';
import { filterModelsByRequested } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/lib/utils.js';

const results = MODELS.map((row, i) => {
  const [modelId, label, intell, ctx, providerKey] = row;
  return {
    idx: i,
    modelId,
    label,
    intell,
    ctx,
    providerKey,
    status: 'up',
    pings: [{ ms: 100, code: '200', ts: Date.now() }]
  };
});

console.log("Static results length:", results.length);

const matches1 = filterModelsByRequested(results, 'minimax-m3', canonicalizeModelId);
console.log("\nMatches for 'minimax-m3':");
for (const m of matches1) {
  console.log(`- ${m.providerKey}/${m.modelId} (status: ${m.status})`);
}

const matches2 = filterModelsByRequested(results, 'minimax/minimax-m3', canonicalizeModelId);
console.log("\nMatches for 'minimax/minimax-m3':");
for (const m of matches2) {
  console.log(`- ${m.providerKey}/${m.modelId} (status: ${m.status})`);
}
