"""NEXUS OS — Bridge module: HMAC auth + JSON-RPC server."""
import hmac, hashlib

class BridgeServer:
    def __init__(self, secret: str):
        self.secret = secret.encode()

    def sign(self, trace: str, payload: str) -> str:
        msg = f"{trace}:{payload}".encode()
        return hmac.new(self.secret, msg, hashlib.sha256).hexdigest()

    def verify(self, trace: str, payload: str, sig: str) -> bool:
        expected = self.sign(trace, payload)
        return hmac.compare_digest(expected, sig)

def sign(secret: str, trace: str, payload: str) -> str:
    return BridgeServer(secret).sign(trace, payload)

def verify(secret: str, trace: str, payload: str, sig: str) -> bool:
    return BridgeServer(secret).verify(trace, payload, sig)