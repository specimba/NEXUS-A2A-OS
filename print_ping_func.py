with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\server.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_line = -1
for i, line in enumerate(lines):
    if "async function ping(" in line:
        start_line = i
        break

if start_line != -1:
    print(f"Found function at line {start_line+1}")
    for j in range(start_line, min(start_line + 50, len(lines))):
        safe_line = lines[j].rstrip().encode('ascii', errors='replace').decode()
        print(f"{j+1}: {safe_line}")
        if safe_line.startswith("}"):
            break
else:
    print("Not found")
