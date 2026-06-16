with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\server.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "MAX_PROACTIVE_RETRIES" in line:
        print(f"{i+1}: {line.strip()}")
