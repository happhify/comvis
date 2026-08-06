FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# app/*_reader.py & app/model_quality.py resolve paths as
# Path(__file__).resolve().parents[1] / "config|outputs|data" -> that
# is /app here, so config/outputs/data must be bind-mounted at /app/*.
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
