import { canonicalizeModelId } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/sources.js';
import { filterModelsByRequested, rankModelsForRouting } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/lib/utils.js';

// Fetch current models from running server
const resp = await fetch('http://127.0.0.1:7352/api/models');
const data = await resp.json();
const results = data.models;

console.log(`Total active models in server: ${results.length}`);

const runTest = (requested) => {
  console.log(`\n=== Testing request: "${requested}" ===`);
  const matches = filterModelsByRequested(results, requested, canonicalizeModelId);
  console.log(`Found ${matches.length} matches:`);
  for (const m of matches) {
    console.log(`  - ${m.providerKey}/${m.modelId} (status: ${m.status}, qos: ${m.qos}, elg: ${m.status !== 'banned' && m.status !== 'disabled' && m.status !== 'excluded'})`);
  }
  
  const ranked = rankModelsForRouting(matches);
  console.log(`Ranked order:`);
  for (const m of ranked) {
    console.log(`  - ${m.providerKey}/${m.modelId} (qos: ${m.qos})`);
  }
};

runTest('minimax-m3');
runTest('minimax/minimax-m3');
