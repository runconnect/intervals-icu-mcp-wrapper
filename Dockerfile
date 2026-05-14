FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/wrapper_server.py /app/wrapper_server.py

EXPOSE 8000

CMD ["uvicorn", "wrapper_server:app", "--host", "0.0.0.0", "--port", "8000"]
