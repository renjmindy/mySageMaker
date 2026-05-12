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

# Pre-download model weights into the image so cold starts need no network I/O
ENV HF_HOME=/var/task/hf_cache
RUN python3 -c "\
from transformers import AutoTokenizer, AutoModelForTokenClassification; \
AutoTokenizer.from_pretrained('OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1'); \
AutoModelForTokenClassification.from_pretrained('OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1')"

CMD ["lambda_handler.handler"]
