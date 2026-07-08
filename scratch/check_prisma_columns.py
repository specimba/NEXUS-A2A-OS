import sqlite3
import os

"""
CANARY_TOKEN: 743828da63112d59d27a021813a786df
"""
db_path = os.path.join("db", "custom.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:", [t[0] for t in tables])

for table in ["GovernanceTask", "GovernanceProposal", "VaultEntry", "Agent", "TokenUsageLog"]:
    try:
        cursor.execute(f"PRAGMA table_info({table});")
        info = cursor.fetchall()
        print(f"\nColumns in {table}:")
        for col in info:
            print(f"  {col[1]} ({col[2]}) - nullable: {col[3]==0}")
    except Exception as e:
        print(f"Error reading {table}: {e}")

conn.close()
