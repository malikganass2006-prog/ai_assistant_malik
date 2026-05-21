import json
import urllib.request
import sys

def post(payload):
    url='http://127.0.0.1:8000/api/automation/desktop'
    data=json.dumps(payload).encode('utf-8')
    req=urllib.request.Request(url,data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text=resp.read().decode('utf-8')
            print('REQUEST:', payload)
            print('RESPONSE:', text)
    except Exception as e:
        print('ERROR for', payload, e)

if __name__=='__main__':
    tests=[
        {"action":"list_directory","path":"."},
        {"action":"run_command","command":"echo hello from test"},
        {"action":"find_errors","path":"models/schemas.py"},
    ]
    for t in tests:
        post(t)
