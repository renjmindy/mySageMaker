FROM public.ecr.aws/lambda/python:3.12

# Install C compiler (Amazon Linux 2023 uses dnf)
RUN dnf install -y gcc gcc-c++ && dnf clean all

WORKDIR /var/task

# Install only what the API needs (no gradio)
RUN pip install --no-cache-dir \
    torch>=2.0.0 \
    transformers>=4.35.0 \
    accelerate>=0.24.0 \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    pydantic>=2.5.0 \
    python-multipart>=0.0.6 \
    python-dotenv>=1.0.0 \
    mangum>=0.17.0

COPY src/ ./src/
COPY api/ ./api/
COPY lambda_handler.py .

CMD ["lambda_handler.handler"]
