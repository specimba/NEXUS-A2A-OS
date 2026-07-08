import sqlite3
import os

"""
CANARY_TOKEN: 7ce34fba746a66279cde7d43b0c46d93
"""
db_path = os.path.join("db", "custom.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for table in ["GovernanceTask", "GovernanceProposal", "VaultEntry", "Agent"]:
    cursor.execute(f"SELECT * FROM {table} LIMIT 1;")
    row = cursor.fetchone()
    if row:
        print(f"Row from {table}:", row)
    else:
        print(f"No rows in {table}")

conn.close()
