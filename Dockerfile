FROM python:3.12-slim

# Install system utilities and image libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Setup Web2IPA system directories
RUN mkdir -p /root/.web2ipa/workspaces /root/.web2ipa/url_cache /root/Web2IPA_Output /root/Web2IPA_Dropzone

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8992

# Expose Web Studio port
EXPOSE 8992

# Run Web2IPA AI Studio
CMD ["python3", "agent.py", "--gui", "--port", "8992"]
