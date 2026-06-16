with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\server.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for j in range(2720, 2800):
    safe_line = lines[j].rstrip().encode('ascii', errors='replace').decode()
    print(f"{j+1}: {safe_line}")
