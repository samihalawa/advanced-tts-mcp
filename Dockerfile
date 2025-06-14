# Multi-stage Dockerfile for Advanced TTS MCP Server
# Optimized for Smithery.ai deployment with Python + Node.js support

# ============================================================================
# Stage 1: Python Dependencies and Model Setup
# ============================================================================
FROM python:3.11-slim as python-base

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for Python
WORKDIR /app/python

# Copy Python requirements and install dependencies
COPY pyproject.toml requirements.txt* ./
COPY src/advanced_tts/ ./src/advanced_tts/

# Install Python dependencies
RUN pip install --no-cache-dir -e . || \
    pip install --no-cache-dir \
    mcp>=1.0.0 \
    fastmcp>=0.9.0 \
    kokoro-onnx>=0.4.0 \
    numpy>=1.24.0 \
    soundfile>=0.12.0 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    python-dotenv>=1.0.0 \
    termcolor>=2.0.0 \
    anyio>=4.0.0

# Download Kokoro models if not present (fallback for development)
RUN if [ ! -f /app/kokoro-v1.0.onnx ]; then \
    echo "Downloading Kokoro models..."; \
    wget -q -O /app/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx || echo "Model download failed - will need to be provided"; \
    wget -q -O /app/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin || echo "Voices download failed - will need to be provided"; \
    fi

# ============================================================================
# Stage 2: Node.js Environment for MCP Server
# ============================================================================
FROM node:18-slim as node-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy TypeScript source
COPY src/typescript/ ./src/
COPY smithery.yaml ./

# Build TypeScript
RUN npm run build || echo "Build failed, copying source files" && \
    mkdir -p dist && \
    cp src/index.ts dist/index.js 2>/dev/null || true

# ============================================================================
# Stage 3: Final Production Image
# ============================================================================
FROM node:18-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python environment from python-base
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin
COPY --from=python-base /app/python/src /app/src

# Copy Node.js application from node-base
COPY --from=node-base /app/node_modules ./node_modules
COPY --from=node-base /app/dist ./dist
COPY --from=node-base /app/package*.json ./
COPY --from=node-base /app/smithery.yaml ./

# Copy Kokoro models (these should be included in build context)
COPY kokoro-v1.0.onnx* ./
COPY voices-v1.0.bin* ./

# Copy any additional model files from python-base as fallback
COPY --from=python-base /app/kokoro-v1.0.onnx* ./ 2>/dev/null || true
COPY --from=python-base /app/voices-v1.0.bin* ./ 2>/dev/null || true

# Create output directory for audio files
RUN mkdir -p /app/audio_output && \
    chmod 755 /app/audio_output

# Ensure Python can find our modules
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Set Node.js path
ENV NODE_PATH="/app/node_modules"

# Configure for both local and hosted deployment
ENV MCP_TRANSPORT=http
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/mcp || exit 1

# Expose port for HTTP mode
EXPOSE 3000

# Make the main script executable
RUN chmod +x dist/index.js 2>/dev/null || chmod +x src/index.ts

# Default command - can be overridden by Smithery
CMD ["node", "dist/index.js"]

# Alternative entry points for debugging
# CMD ["node", "src/index.ts"]  # For development
# CMD ["python3", "-m", "src.advanced_tts.server"]  # For Python mode

# ============================================================================
# Build Instructions:
# 
# For local development:
#   docker build -t advanced-tts-mcp .
#   docker run -p 3000:3000 -e MCP_TRANSPORT=http advanced-tts-mcp
#
# For Smithery deployment:
#   The platform will automatically build using this Dockerfile
#   and configure the runtime environment according to smithery.yaml
# ============================================================================