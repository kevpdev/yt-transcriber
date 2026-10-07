FROM python:3.12-slim

WORKDIR /srv
RUN pip install --no-cache-dir uv==0.12.23
ENV UV_PROJECT_ENVIRONMENT=/opt/venv VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH
COPY pyproject.toml uv.lock ./
# yt-dlp is locked in uv.lock then upgraded at build: a --no-cache rebuild follows YouTube changes.
RUN uv sync --frozen --no-install-project --no-dev --group gpu \
    && uv pip install --upgrade yt-dlp

COPY app app
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV HF_HOME=/hf
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "--factory", "app.main:build_app", "--host", "0.0.0.0", "--port", "8000"]
