"""Tests for Bridge Token Headers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from nexus_os.bridge.server import jsonrpc_result

def test_jsonrpc_has_token_headers():
    res = jsonrpc_result({"data": "ok"}, trace_id="tr-123", input_tokens=50, output_tokens=100)
    assert "x-nexus-input-tokens" in res
    assert res["x-nexus-input-tokens"] == 50
    assert "x-nexus-output-tokens" in res
    assert res["x-nexus-output-tokens"] == 100
    assert res["trace_id"] == "tr-123"

def test_smart_pre_filter_security_blocks():
    from nexus_os.bridge.server import scan_payload_for_anomalies
    
    # 1. Verify safe payload passes
    safe_payload = {"description": "Perform normal data science task: import pandas as pd"}
    assert not scan_payload_for_anomalies(safe_payload)

    # 2. Verify benign state CSV passes
    benign_csv_payload = {"record": "id,action,timestamp\n12,select,2026-05-23"}
    assert not scan_payload_for_anomalies(benign_csv_payload)

    # 3. Verify SQL injection inside CSV fails
    malicious_csv_payload = {"description": "name,email,role,action\nadmin,admin@corp.com,DROP TABLE users;--,execute"}
    assert scan_payload_for_anomalies(malicious_csv_payload)

    # 4. Verify code injection fails
    malicious_code_payload = {"context": "eval('__import__(\"os\").system(\"ls\")')"}
    assert scan_payload_for_anomalies(malicious_code_payload)
