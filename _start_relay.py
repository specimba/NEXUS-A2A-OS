import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nexus_os.relay.model_relay import app
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=7355)
