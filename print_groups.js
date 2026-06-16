import { MODELS, sources, canonicalizeModelId } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/sources.js';
import { buildModelGroups } from 'file:///C:/Users/speci.000/AppData/Roaming/npm/node_modules/modelrelay/lib/utils.js';

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

const groups = buildModelGroups(results, canonicalizeModelId);
console.log(`Total groups: ${groups.length}`);

for (const group of groups) {
  if (group.id.includes('minimax') || group.id.includes('kimi')) {
    console.log(`Group ID: ${group.id}`);
    console.log(`  Label: ${group.label}`);
    console.log(`  Aliases: ${group.aliases.join(', ')}`);
    console.log(`  Models:`);
    for (const m of group.models) {
      console.log(`    - ${m.providerKey}/${m.modelId}`);
    }
  }
}
