FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
# yt-dlp n'est pas figé : une reconstruction --no-cache suit les changements de YouTube.
RUN pip install --no-cache-dir -r requirements.txt \
    nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

COPY app app
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV HF_HOME=/hf
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "--factory", "app.main:build_app", "--host", "0.0.0.0", "--port", "8000"]
