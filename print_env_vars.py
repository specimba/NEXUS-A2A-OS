with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\config.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_line = -1
for i, line in enumerate(lines):
    if "PROVIDER_MODEL_ID_ENV_VARS" in line:
        start_line = i
        break

if start_line != -1:
    print(f"Found at line {start_line+1}")
    for j in range(max(0, start_line - 2), min(start_line + 25, len(lines))):
        safe_line = lines[j].rstrip().encode('ascii', errors='replace').decode()
        print(f"{j+1}: {safe_line}")
else:
    print("Not found")
