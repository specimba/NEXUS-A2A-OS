import os

lib_dir = r"C:\Users\speci.000\AppData\Roaming\npm\node_modules\modelrelay\lib"
files = [os.path.join(lib_dir, f) for f in os.listdir(lib_dir) if f.endswith(".js")]

for fp in files:
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    if "buildProviderRequestBody" in content:
        print(f"Found in {os.path.basename(fp)}")
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "buildProviderRequestBody" in line:
                print(f"  {i+1}: {line.strip()}")
