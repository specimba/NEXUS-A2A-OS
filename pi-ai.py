#!/usr/bin/env python3;import
os,sys,requests;key=os.getenv("OLLAMA_CLOUD_KEY");exec("if
not key:print('❌ OLLAMA_CLOUD_KEY not set');sys.exit(1)")
exec("def
ask(q):r=requests.post('https://api.ollama.cloud/v1/chat/complask(q):r=requests.post('https://api.ollama.cloud/v1/hat/completions',json={'model':'qwen3-coder-next:cloud','messages':[{'rotions',json={'model':'qwen3-coder-next:cloud','messages':[{'role':'user','content':q}],'temperature':0.1},headers={'Authorizae':'user','content':q}],'temperature':0.1},headers={'Authorization':f'Bearer {key}'},timeout=30);return
r.json()['choices'][0]['message']['content']")
if __name__=="__main__":print(f"\n🤖 Qwen:
{ask(sys.argv[1])}\n")