with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\config.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for j in range(260, 290):
    safe_line = lines[j].rstrip().encode('ascii', errors='replace').decode()
    print(f"{j+1}: {safe_line}")
