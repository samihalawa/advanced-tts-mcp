# Advanced TTS MCP Server - Smithery.ai Deployment Guide

## Overview

This guide covers deploying the Advanced TTS MCP Server to Smithery.ai, the premier platform for hosting and distributing Model Context Protocol servers. Smithery provides both local and hosted deployment options with automatic scaling and configuration management.

## 🚀 Quick Deployment to Smithery

### Prerequisites

1. **GitHub Repository**: Your code must be in a public GitHub repository
2. **Smithery Account**: Sign up at [smithery.ai](https://smithery.ai)
3. **Model Files**: Ensure `kokoro-v1.0.onnx` and `voices-v1.0.bin` are included or accessible

### Automatic Deployment

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Ready for Smithery deployment"
   git push origin main
   ```

2. **Connect to Smithery**:
   - Go to [smithery.ai](https://smithery.ai)
   - Connect your GitHub account
   - Import the `advanced-tts-mcp` repository

3. **Configure Deployment**:
   - Smithery will automatically detect the `smithery.yaml` configuration
   - Set your preferred configuration values
   - Click "Deploy" to build and host your server

4. **Use Your Server**:
   - Get your server URL from the Smithery dashboard
   - Add to Claude Desktop or use via Smithery CLI

## 📋 Configuration Options

### Smithery Configuration Schema

The server supports the following configuration parameters:

```yaml
# smithery.yaml - automatically detected by Smithery
configSchema:
  type: object
  properties:
    defaultVoice:
      type: string
      description: "Default voice for TTS synthesis"
      default: "af_heart"
      enum: ["af_heart", "af_sky", "af_bella", "af_sarah", "af_nicole", 
             "am_adam", "am_michael", "bf_emma", "bf_isabella", "bm_lewis"]
    
    defaultSpeed:
      type: number
      description: "Default speech speed"
      default: 1.0
      minimum: 0.25
      maximum: 3.0
    
    defaultEmotion:
      type: string
      description: "Default voice emotion"
      default: "neutral"
      enum: ["neutral", "happy", "excited", "calm", "serious", "casual", "confident"]
    
    defaultPacing:
      type: string
      description: "Default speech pacing style"  
      default: "natural"
      enum: ["natural", "conversational", "presentation", "tutorial", "narrative", "fast", "slow"]
    
    enableFileOutput:
      type: boolean
      description: "Enable audio file output by default"
      default: false
    
    maxTextLength:
      type: integer
      description: "Maximum text length per request"
      default: 10000
      minimum: 100
      maximum: 50000
    
    debugMode:
      type: boolean
      description: "Enable debug logging"
      default: false
```

### Example Configurations

#### Professional Presentation Setup
```json
{
  "defaultVoice": "af_sarah",
  "defaultSpeed": 0.9,
  "defaultEmotion": "confident",
  "defaultPacing": "presentation",
  "enableFileOutput": true,
  "maxTextLength": 25000
}
```

#### Casual Tutorial Setup
```json
{
  "defaultVoice": "am_michael",
  "defaultSpeed": 1.0,
  "defaultEmotion": "casual",
  "defaultPacing": "tutorial",
  "enableFileOutput": false,
  "maxTextLength": 15000
}
```

#### High-Volume Processing
```json
{
  "defaultVoice": "af_heart",
  "defaultSpeed": 1.2,
  "defaultEmotion": "neutral",
  "defaultPacing": "fast",
  "enableFileOutput": false,
  "maxTextLength": 50000
}
```

## 🔧 Local Development with Smithery CLI

### Installation

```bash
# Install Smithery CLI
npm install -g @smithery/cli

# Clone and setup
git clone https://github.com/samihalawa/advanced-tts-mcp.git
cd advanced-tts-mcp
npm install
```

### Development Commands

```bash
# Start development server with hot-reload
npm run smithery:dev

# Build for production
npm run smithery:build

# Test with MCP Inspector
npm run smithery:test

# Local HTTP testing
npm run start:http
curl http://localhost:3000/mcp
```

### Docker Development

```bash
# Build Docker image
npm run docker:build

# Run locally
npm run docker:run

# Test HTTP endpoint
npm run test:http
```

## 🏗️ Architecture Details

### Hybrid Python + TypeScript Implementation

The server uses a unique hybrid architecture:

1. **TypeScript Frontend**: Handles MCP protocol, HTTP endpoints, and Smithery integration
2. **Python Backend**: Manages Kokoro TTS engine and audio processing
3. **Shared Models**: Consistent data models across both runtimes

### Transport Support

- **STDIO Transport**: For local Claude Desktop integration
- **HTTP Transport**: For Smithery hosted deployment with streamable connections
- **Auto-Detection**: Automatically selects appropriate transport based on environment

### Model File Handling

The server requires Kokoro model files (~337MB total):

1. **Build-time Inclusion**: Models copied during Docker build if present
2. **Runtime Download**: Fallback download during container startup
3. **Volume Mounting**: For development, mount models as volumes

## 🔒 Security Considerations

### Authentication

- **Local Mode**: No authentication required (localhost only)
- **Hosted Mode**: Smithery handles authentication and token management
- **API Security**: All sensitive data passed via environment variables

### Data Privacy

- **Local Processing**: All TTS synthesis happens locally/in-container
- **No Data Retention**: Audio files are temporary and auto-cleaned
- **Ephemeral Storage**: Hosted deployment uses temporary storage only

### Resource Limits

- **Memory**: ~2GB RAM recommended for optimal performance
- **Storage**: ~500MB for models + temporary audio files
- **Network**: Minimal requirements (model download only)

## 📊 Performance Optimization

### Deployment Modes

1. **Development Mode**:
   ```bash
   MCP_TRANSPORT=stdio npm run dev
   ```

2. **Production HTTP Mode**:
   ```bash
   MCP_TRANSPORT=http PORT=3000 npm start
   ```

3. **Smithery Hosted Mode**:
   - Automatically configured by platform
   - Optimized for serverless scaling

### Caching Strategy

- **Model Loading**: Models loaded once on server startup
- **Audio Processing**: No persistent caching (ephemeral environment)
- **Configuration**: Cached per request lifecycle

### Scaling Considerations

- **Horizontal Scaling**: Each instance handles independent requests
- **Cold Starts**: ~2-3 seconds for model initialization
- **Warm Instances**: Sub-second response times

## 🐛 Troubleshooting

### Common Issues

#### 1. Model Files Missing
**Error**: `Model file not found: kokoro-v1.0.onnx`
**Solution**: 
```bash
# Download models manually
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

#### 2. Python Dependencies Error
**Error**: `No module named 'kokoro_onnx'`
**Solution**: 
```bash
# Rebuild Docker image
docker build --no-cache -t advanced-tts-mcp .
```

#### 3. HTTP Endpoint Not Responding
**Error**: Connection refused on port 3000
**Solution**:
```bash
# Check environment variables
export MCP_TRANSPORT=http
export PORT=3000
npm start
```

#### 4. Audio Processing Fails
**Error**: `FFmpeg not found`
**Solution**: Ensure FFmpeg is installed in container (handled by Dockerfile)

### Debug Mode

Enable debug logging:
```json
{
  "debugMode": true
}
```

Check logs:
```bash
# Local development
npm run dev 2>debug.log

# Docker logs
docker logs <container-id>

# Smithery logs (available in dashboard)
```

### Health Checks

The server includes health check endpoints:

```bash
# Basic health check
curl http://localhost:3000/mcp

# Voice list (validates models loaded)
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "call_tool", "params": {"name": "get_voices", "arguments": {}}}'
```

## 🔄 Updates and Maintenance

### Version Updates

1. **Update Code**: Push changes to GitHub
2. **Automatic Rebuild**: Smithery detects changes and rebuilds
3. **Rolling Deployment**: Zero-downtime updates

### Model Updates

To update Kokoro models:
1. Replace model files in repository
2. Update Dockerfile if needed
3. Trigger rebuild on Smithery

### Configuration Updates

Update `smithery.yaml` and redeploy for configuration schema changes.

## 📞 Support

### Documentation
- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Smithery Platform**: [smithery.ai/docs](https://smithery.ai/docs)
- **Kokoro TTS**: [github.com/thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)

### Community
- **GitHub Issues**: [advanced-tts-mcp/issues](https://github.com/samihalawa/advanced-tts-mcp/issues)
- **Smithery Discord**: Community support and discussions
- **MCP Community**: Official MCP protocol discussions

### Professional Support
For enterprise deployments and custom modifications, contact the maintainers through GitHub.

---

**Ready to deploy?** Push your code to GitHub and connect to Smithery.ai for instant deployment of your Advanced TTS MCP Server!