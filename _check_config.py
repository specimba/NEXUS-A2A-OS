import json
with open(r'C:\Users\speci.000\.modelrelay.json') as f:
    cfg = json.load(f)
print('Providers:', list(cfg.get('providers', {}).keys()))
print('API keys:', list(cfg.get('apiKeys', {}).keys()))
for k in ['openai-compatible:siliconflow', 'openai-compatible:deepinfra', 'openai-compatible:googleai']:
    has_key = k in cfg.get('apiKeys', {})
    has_prov = k in cfg.get('providers', {})
    print(f'{k}: key={has_key}, prov={has_prov}')