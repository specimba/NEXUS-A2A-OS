with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\server.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "pingModel" in line or "ping(" in line:
        safe_line = line.strip().encode('ascii', errors='replace').decode()
        print(f"{i+1}: {safe_line}")
