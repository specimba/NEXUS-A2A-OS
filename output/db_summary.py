import sqlite3, os

dbs = [
    r'C:\Users\speci.000\Documents\NEXUS\nexus_governance.db',
    r'C:\Users\speci.000\Documents\NEXUS\db\custom.db',
    r'C:\Users\speci.000\Documents\NEXUS\.nexus\csi_audit.db',
    r'C:\Users\speci.000\Documents\NEXUS\.nexus\governance-rest.db',
]

for db_path in dbs:
    sz = os.path.getsize(db_path)
    print(f"=== {os.path.basename(db_path)} ({sz:,} bytes) ===")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        for (tname,) in tables:
            count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
            cols = cur.execute(f'PRAGMA table_info("{tname}")').fetchall()
            col_names = [c[1] for c in cols]
            print(f"  table: {tname} | rows: {count} | cols: {col_names}")
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
