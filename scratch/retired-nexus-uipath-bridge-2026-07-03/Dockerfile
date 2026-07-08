FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY nexus_uipath_bridge/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY nexus_uipath_bridge ./nexus_uipath_bridge

EXPOSE 8080
CMD ["uvicorn", "nexus_uipath_bridge.app:app", "--host", "0.0.0.0", "--port", "8080"]
