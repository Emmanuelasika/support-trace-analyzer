FROM python:3.12-slim
WORKDIR /workspace
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN pip install --no-cache-dir .
ENTRYPOINT ["tracekit"]
CMD ["--help"]
