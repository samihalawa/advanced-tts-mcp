# Optimized Dockerfile for Advanced TTS MCP Server
# TypeScript-only implementation for Smithery.ai deployment

FROM node:18-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install all dependencies (including dev dependencies for build)
RUN npm ci

# Copy source code
COPY src/ ./src/
COPY smithery.yaml ./

# Build TypeScript
RUN npm run build

# Remove dev dependencies after build
RUN npm prune --production

# Create output directory for audio files
RUN mkdir -p /app/audio_output && \
    chmod 755 /app/audio_output

# Configure for deployment
ENV NODE_ENV=production
ENV MCP_TRANSPORT=http
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/mcp || exit 1

# Expose port
EXPOSE 3000

# Start the server
CMD ["node", "dist/index.js"]

# ============================================================================
# Build Instructions:
# 
# For local development:
#   docker build -t advanced-tts-mcp .
#   docker run -p 3000:3000 -e MCP_TRANSPORT=http advanced-tts-mcp
#
# For Smithery deployment:
#   The platform will automatically build using this Dockerfile
# ============================================================================