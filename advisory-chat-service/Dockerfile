FROM python:3.11-slim
WORKDIR /app

# CPU-only torch wheel first — sentence-transformers depends on torch, and
# without this pip would resolve the default CUDA build and pull ~GBs of
# nvidia-* packages (cublas, cuda-bindings, ...) that this CPU service never
# uses. Pinning the CPU wheel keeps the image small and the build reliable.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x start.sh
EXPOSE 8000
CMD ["bash", "start.sh"]
