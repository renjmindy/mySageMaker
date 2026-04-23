FROM public.ecr.aws/lambda/python:3.11

COPY handler.py ${LAMBDA_TASK_ROOT}/

RUN pip install --no-cache-dir boto3

CMD ["handler.lambda_handler"]
