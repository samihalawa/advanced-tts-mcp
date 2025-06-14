"""
Data models for Advanced TTS MCP Server.
"""

from typing import Optional, List, Literal, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class VoiceEmotion(str, Enum):
    """Available voice emotions for natural speech."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    SERIOUS = "serious"
    CASUAL = "casual"
    CONFIDENT = "confident"


class PacingStyle(str, Enum):
    """Speech pacing styles for different use cases."""
    NATURAL = "natural"
    CONVERSATIONAL = "conversational"
    PRESENTATION = "presentation"
    TUTORIAL = "tutorial"
    NARRATIVE = "narrative"
    FAST = "fast"
    SLOW = "slow"


class AudioFormat(str, Enum):
    """Supported audio output formats."""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"


class VoiceConfig(BaseModel):
    """Voice configuration settings."""
    voice_id: str = Field(default="af_heart", description="Voice identifier")
    speed: float = Field(default=1.0, ge=0.25, le=3.0, description="Speech speed (0.25-3.0)")
    emotion: VoiceEmotion = Field(default=VoiceEmotion.NEUTRAL, description="Voice emotion")
    pacing: PacingStyle = Field(default=PacingStyle.NATURAL, description="Speech pacing style")
    volume: float = Field(default=1.0, ge=0.1, le=2.0, description="Audio volume (0.1-2.0)")
    
    @validator('speed')
    def validate_speed(cls, v):
        if not 0.25 <= v <= 3.0:
            raise ValueError('Speed must be between 0.25 and 3.0')
        return v


class TTSRequest(BaseModel):
    """Text-to-speech request model."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig, description="Voice settings")
    output_format: AudioFormat = Field(default=AudioFormat.WAV, description="Audio output format")
    streaming: bool = Field(default=True, description="Enable streaming playback")
    save_file: bool = Field(default=False, description="Save audio to file")
    filename: Optional[str] = Field(default=None, description="Custom filename for saved audio")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()


class BatchTTSRequest(BaseModel):
    """Batch text-to-speech request for multiple segments."""
    segments: List[str] = Field(..., min_items=1, description="List of text segments")
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig, description="Voice settings")
    output_format: AudioFormat = Field(default=AudioFormat.WAV, description="Audio output format")
    merge_output: bool = Field(default=True, description="Merge segments into single file")
    segment_pause: float = Field(default=0.5, ge=0.0, le=5.0, description="Pause between segments (seconds)")
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique batch ID")


class AudioSegment(BaseModel):
    """Audio segment data."""
    audio_data: bytes = Field(..., description="Raw audio data")
    sample_rate: int = Field(..., description="Audio sample rate")
    duration: float = Field(..., description="Duration in seconds")
    format: AudioFormat = Field(..., description="Audio format")


class AudioOutput(BaseModel):
    """Audio output result."""
    request_id: str = Field(..., description="Request identifier")
    segments: List[AudioSegment] = Field(..., description="Audio segments")
    total_duration: float = Field(..., description="Total duration in seconds")
    file_path: Optional[str] = Field(default=None, description="Saved file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TTSStatus(BaseModel):
    """TTS processing status."""
    request_id: str = Field(..., description="Request identifier")
    status: Literal["queued", "processing", "completed", "error", "cancelled"] = Field(..., description="Processing status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    message: Optional[str] = Field(default=None, description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class VoiceInfo(BaseModel):
    """Voice information model."""
    voice_id: str = Field(..., description="Voice identifier")
    name: str = Field(..., description="Human-readable voice name")
    language: str = Field(..., description="Language code")
    gender: Literal["male", "female", "neutral"] = Field(..., description="Voice gender")
    description: str = Field(..., description="Voice description")
    sample_rate: int = Field(..., description="Default sample rate")
    supported_emotions: List[VoiceEmotion] = Field(..., description="Supported emotions")
    quality: Literal["standard", "high", "premium"] = Field(..., description="Voice quality")


class ServerConfig(BaseModel):
    """Server configuration model."""
    model_path: str = Field(default="kokoro-v1.0.onnx", description="Path to Kokoro model file")
    voices_path: str = Field(default="voices-v1.0.bin", description="Path to voices file")
    output_dir: str = Field(default="./audio_output", description="Output directory for saved files")
    max_queue_size: int = Field(default=100, description="Maximum queue size")
    enable_streaming: bool = Field(default=True, description="Enable streaming playback")
    auto_cleanup: bool = Field(default=True, description="Auto-cleanup temporary files")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval in seconds")
    max_text_length: int = Field(default=10000, description="Maximum text length per request")
    default_voice: str = Field(default="af_heart", description="Default voice ID")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", description="Logging level")