# Advanced TTS MCP Server

A high-quality, feature-rich Text-to-Speech MCP server powered by Kokoro neural voices. Designed for professional applications requiring natural, expressive speech synthesis with advanced controls.

## ✨ Features

### 🎯 **Advanced Voice Control**
- **10 High-Quality Voices** - Male and female voices with distinct personalities
- **Emotion Control** - Neutral, happy, excited, calm, serious, casual, confident
- **Dynamic Pacing** - Natural, conversational, presentation, tutorial, narrative modes
- **Speed & Volume** - Precise control from 0.25x to 3.0x speed, 0.1x to 2.0x volume

### 🚀 **Professional Capabilities**
- **Streaming Audio** - Real-time synthesis and playback
- **Batch Processing** - Handle multiple text segments efficiently  
- **Multiple Formats** - WAV, MP3, FLAC, OGG output support
- **Natural Speech Enhancement** - Automatic pause insertion and emotion markers
- **Queue Management** - Handle multiple concurrent requests

### 🔧 **MCP Integration**
- **6 Powerful Tools** - Complete synthesis, batch processing, voice management
- **2 Rich Resources** - Voice capabilities and usage examples
- **Real-time Status** - Track processing progress and manage requests
- **File Management** - Save, list, and organize audio outputs

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- macOS, Linux, or Windows
- FFmpeg (for MP3/format conversion)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/samihalawa/advanced-tts-mcp.git
cd advanced-tts-mcp
```

2. **Install dependencies**
```bash
pip install -e .
```

3. **Download Kokoro models** (required)
```bash
# Download model files (~337MB total)
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

4. **Configure Claude Desktop**

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "advanced-tts": {
      "command": "python",
      "args": ["-m", "advanced_tts.server"],
      "cwd": "/path/to/advanced-tts-mcp"
    }
  }
}
```

5. **Start using!**

Restart Claude Desktop and start synthesizing with natural, expressive voices.

## 🎙️ Available Voices

| Voice ID | Name | Gender | Description |
|----------|------|--------|-------------|
| `af_heart` | Heart | Female | Warm, friendly voice (default) |
| `af_sky` | Sky | Female | Clear, bright voice |
| `af_bella` | Bella | Female | Elegant, sophisticated voice |
| `af_sarah` | Sarah | Female | Professional, confident voice |
| `af_nicole` | Nicole | Female | Gentle, soothing voice |
| `am_adam` | Adam | Male | Strong, authoritative voice |
| `am_michael` | Michael | Male | Friendly, approachable voice |
| `bf_emma` | Emma | Female | Young, energetic voice |
| `bf_isabella` | Isabella | Female | Mature, expressive voice |
| `bm_lewis` | Lewis | Male | Deep, resonant voice |

## 📚 Usage Examples

### Basic Synthesis
```python
# Simple text-to-speech
await synthesize_speech(
    text="Hello! Welcome to Advanced TTS.",
    voice_id="af_heart"
)
```

### Emotional Expression
```python
# Excited announcement
await synthesize_speech(
    text="This is amazing news! You're going to love this new feature!",
    voice_id="af_heart",
    emotion="excited",
    pacing="conversational",
    speed=1.1
)
```

### Professional Presentation
```python
# Tutorial narration
await synthesize_speech(
    text="Step one: Open your browser. Step two: Navigate to the website.",
    voice_id="am_adam", 
    emotion="calm",
    pacing="tutorial",
    speed=0.9
)
```

### Batch Processing
```python
# Multiple segments with pauses
await batch_synthesize(
    segments=[
        "Welcome to our presentation.",
        "Today we'll cover three main topics.", 
        "Let's begin with the first topic."
    ],
    voice_id="af_sarah",
    emotion="confident",
    pacing="presentation",
    merge_output=True,
    segment_pause=1.0,
    save_file=True
)
```

## 🛠️ Available Tools

### `synthesize_speech`
Convert text to natural speech with full control over voice characteristics.

**Parameters:**
- `text` - Text to synthesize (max 10,000 chars)
- `voice_id` - Voice selection (see table above)
- `speed` - Speech rate (0.25-3.0)
- `emotion` - Voice emotion (neutral, happy, excited, calm, serious, casual, confident)
- `pacing` - Speech style (natural, conversational, presentation, tutorial, narrative, fast, slow)
- `volume` - Audio volume (0.1-2.0)
- `output_format` - File format (wav, mp3, flac, ogg)
- `save_file` - Save to file (boolean)
- `filename` - Custom filename

### `batch_synthesize` 
Process multiple text segments efficiently with optional merging.

**Parameters:**
- `segments` - List of text segments
- `merge_output` - Combine into single file
- `segment_pause` - Pause between segments (0.0-5.0s)
- All synthesis parameters from above

### `get_voices`
Retrieve complete voice information and capabilities.

### `get_status` 
Check processing status for synthesis requests.

### `cancel_request`
Cancel active synthesis operations.

### `list_output_files`
Browse saved audio files with metadata.

## 🎛️ Voice Controls

### Emotions
- **Neutral** - Standard, professional tone
- **Happy** - Upbeat, cheerful expression
- **Excited** - Enthusiastic, energetic delivery
- **Calm** - Relaxed, soothing tone
- **Serious** - Formal, authoritative delivery
- **Casual** - Relaxed, conversational style
- **Confident** - Assured, professional tone

### Pacing Styles  
- **Natural** - Balanced, human-like rhythm
- **Conversational** - Casual discussion pace
- **Presentation** - Professional speaking rhythm
- **Tutorial** - Educational, clear delivery
- **Narrative** - Storytelling pace
- **Fast** - Quick delivery (1.2x base speed)
- **Slow** - Deliberate delivery (0.8x base speed)

## 🎵 Audio Formats

| Format | Quality | Use Case |
|--------|---------|----------|
| **WAV** | Uncompressed | Highest quality, editing |
| **MP3** | Compressed | Web, streaming, sharing |
| **FLAC** | Lossless | Archival, high-quality storage |
| **OGG** | Compressed | Open source alternative |

## 🔧 Configuration

### Environment Variables
```bash
# Model paths (optional)
KOKORO_MODEL_PATH=./kokoro-v1.0.onnx
KOKORO_VOICES_PATH=./voices-v1.0.bin

# Output settings
TTS_OUTPUT_DIR=./audio_output
TTS_MAX_QUEUE_SIZE=100

# Audio settings  
TTS_DEFAULT_VOICE=af_heart
TTS_ENABLE_STREAMING=true
```

### Server Configuration
```python
config = ServerConfig(
    model_path="./kokoro-v1.0.onnx",
    voices_path="./voices-v1.0.bin", 
    output_dir="./audio_output",
    max_queue_size=100,
    enable_streaming=True,
    default_voice="af_heart"
)
```

## 🏗️ Architecture

```
├── src/advanced_tts/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # MCP server implementation  
│   ├── engine.py            # Kokoro TTS engine wrapper
│   ├── models.py            # Data models and validation
│   └── utils.py             # Utility functions
├── pyproject.toml           # Project configuration
├── README.md               # Documentation
└── LICENSE                 # MIT License
```

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional voice models
- Real-time streaming synthesis
- Advanced audio effects
- Multi-language support
- Performance optimizations

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **Kokoro TTS** - High-quality neural voice synthesis
- **MCP Protocol** - Seamless AI model integration
- **FastMCP** - Efficient server framework

---

**Developed by [Sami Halawa](https://github.com/samihalawa)**

*Transform your text into natural, expressive speech with Advanced TTS MCP Server.*