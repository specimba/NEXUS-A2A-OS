import requests, time, sys
for i in range(20):
    try:
        r = requests.get('http://127.0.0.1:7352/api/models', timeout=3)
        if r.ok and r.json().get('models'):
            d = r.json()
            ms = d.get('models', [])
            up = [m for m in ms if m.get('status') == 'up']
            provs = {}
            for m in ms:
                p = m.get('provider', m.get('providerKey', '?'))
                s = m.get('status', '?')
                provs.setdefault(p, {'up': 0, 'total': 0})
                provs[p]['total'] += 1
                if s == 'up':
                    provs[p]['up'] += 1
            print(f'{len(up)} UP / {len(ms)} total - {len(provs)} providers')
            for p, c in sorted(provs.items(), key=lambda x: -x[1]['total']):
                print(f'  {p:35s} {c["up"]:3d}/{c["total"]:3d} up')
            sys.exit(0)
    except:
        pass
    time.sleep(1)
print('Not started after 20s')
sys.exit(1)