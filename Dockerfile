
FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install RIFE (Frame Interpolation)
RUN wget https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-ubuntu.zip && \
    unzip rife-ncnn-vulkan-20221029-ubuntu.zip && \
    chmod +x rife-ncnn-vulkan-20221029-ubuntu/rife-ncnn-vulkan && \
    mv rife-ncnn-vulkan-20221029-ubuntu/rife-ncnn-vulkan /usr/local/bin/rife-ncnn-vulkan && \
    rm -rf rife-ncnn-vulkan-20221029-ubuntu*

# Install RealESRGAN (Upscaling)
RUN wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    unzip realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    chmod +x realesrgan-ncnn-vulkan && \
    mv realesrgan-ncnn-vulkan /usr/local/bin/realesrgan-ncnn-vulkan && \
    rm -f realesrgan-ncnn-vulkan-20220424-ubuntu.zip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY README.md .
RUN mkdir -p src/utility_classes
ENTRYPOINT ["python", "src/main.py"]
CMD ["--help"]