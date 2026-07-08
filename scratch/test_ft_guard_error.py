import urllib.request
import urllib.error
import json

"""
CANARY_TOKEN: b3dd4bf77cb775b6318efa683373be03
"""
def main():
    url = 'http://127.0.0.1:11435/api/generate'
    data = {
        'model': 'qwen2.5-guard:1.5b',
        'prompt': 'hello',
        'stream': False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'}
    )
    try:
        response = urllib.request.urlopen(req)
        body = response.read().decode()
        print('SUCCESS:', body)
    except urllib.error.HTTPError as e:
        print('CODE:', e.code)
        try:
            body = e.fp.read().decode()
            print('BODY:', body)
        except Exception as read_err:
            print('FAILED TO READ BODY:', read_err)
    except Exception as err:
        print('OTHER ERROR:', err)

if __name__ == '__main__':
    main()
