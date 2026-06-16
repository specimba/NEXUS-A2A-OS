with open(r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib\utils.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_func(name):
    start_line = -1
    for i, line in enumerate(lines):
        if f"function {name}" in line:
            start_line = i
            break
    if start_line != -1:
        print(f"=== {name} ===")
        for j in range(start_line, min(start_line + 50, len(lines))):
            safe_line = lines[j].rstrip().encode('ascii', errors='replace').decode()
            print(f"{j+1}: {safe_line}")
            if safe_line.startswith("}"):
                break
        print()

print_func("getModelGroupId")
print_func("getModelGroupKey")
