# Linux runtime for the advisory runner on an x86 laptop.
# The ExecuTorch 1.5.1 Windows wheel has no Llama kernels (custom_sdpa,
# update_cache, embedding_byte), the Linux wheel does.
FROM python:3.10-slim
RUN pip install --no-cache-dir torch==2.14.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir executorch==1.5.1 psutil==7.2.2
WORKDIR /work
