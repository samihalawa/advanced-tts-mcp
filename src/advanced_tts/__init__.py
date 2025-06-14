"""
Advanced TTS MCP Server

High-quality neural text-to-speech synthesis with enhanced features including:
- Local Kokoro TTS engine with natural voice synthesis
- Streaming audio processing and playback
- Advanced voice controls (speed, emotion, pacing)
- Batch processing for long content
- Multiple export formats
- Queue management with cancellation support
"""

__version__ = "1.0.0"
__author__ = "Sami Halawa"
__email__ = "sami@example.com"

from .server import AdvancedTTSServer
from .engine import KokoroEngine
from .models import TTSRequest, VoiceConfig, AudioOutput

__all__ = [
    "AdvancedTTSServer",
    "KokoroEngine", 
    "TTSRequest",
    "VoiceConfig",
    "AudioOutput",
]