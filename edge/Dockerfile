FROM python:3.11-slim
WORKDIR /app
# copy edge requirements specifically (build context will be repo root)
COPY edge/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# copy entire repo so `sensors/` package is available
COPY . .
CMD ["python", "-m", "edge.collector"]
