"""
Enhanced Kokoro TTS Engine with advanced features.
"""

import asyncio
import tempfile
import subprocess
import wave
import numpy as np
import soundfile as sf
from typing import Optional, List, Tuple, AsyncGenerator
from pathlib import Path
import logging
import re
from dataclasses import dataclass

from kokoro_onnx import Kokoro

from .models import (
    VoiceConfig, VoiceEmotion, PacingStyle, AudioFormat, 
    AudioSegment, VoiceInfo, TTSRequest
)

logger = logging.getLogger(__name__)


@dataclass
class NaturalSpeechEnhancer:
    """Enhances text for more natural speech patterns."""
    
    @staticmethod
    def add_natural_pauses(text: str, pacing: PacingStyle) -> str:
        """Add natural pauses based on pacing style."""
        if pacing == PacingStyle.CONVERSATIONAL:
            # Add brief pauses for conversational flow
            text = re.sub(r'([.!?])\s+', r'\1... ', text)
            text = re.sub(r'([,;:])\s+', r'\1.. ', text)
        elif pacing == PacingStyle.TUTORIAL:
            # Longer pauses for educational content
            text = re.sub(r'([.!?])\s+', r'\1.... ', text)
            text = re.sub(r'(\d+\.)\s+', r'\1... ', text)  # After numbered points
        elif pacing == PacingStyle.PRESENTATION:
            # Professional presentation pacing
            text = re.sub(r'([.!?])\s+', r'\1... ', text)
            text = re.sub(r'(\w+:)\s+', r'\1.. ', text)  # After colons
        
        return text
    
    @staticmethod
    def apply_emotion_markers(text: str, emotion: VoiceEmotion) -> str:
        """Apply subtle emotional markers to text."""
        if emotion == VoiceEmotion.EXCITED:
            # Add emphasis to certain words
            text = re.sub(r'\b(amazing|awesome|incredible|fantastic|great)\b', 
                         r'*\1*', text, flags=re.IGNORECASE)
        elif emotion == VoiceEmotion.CASUAL:
            # Add casual contractions
            replacements = {
                r'\byou are\b': "you're",
                r'\bit is\b': "it's", 
                r'\bthat is\b': "that's",
                r'\bcannot\b': "can't"
            }
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def enhance_for_speech(text: str, voice_config: VoiceConfig) -> str:
        """Apply all natural speech enhancements."""
        enhanced = text
        enhanced = NaturalSpeechEnhancer.add_natural_pauses(enhanced, voice_config.pacing)
        enhanced = NaturalSpeechEnhancer.apply_emotion_markers(enhanced, voice_config.emotion)
        return enhanced


class KokoroEngine:
    """Enhanced Kokoro TTS engine with advanced features."""
    
    def __init__(self, model_path: str = "kokoro-v1.0.onnx", voices_path: str = "voices-v1.0.bin"):
        """Initialize the Kokoro engine."""
        self.model_path = model_path
        self.voices_path = voices_path
        self.engine: Optional[Kokoro] = None
        self.enhancer = NaturalSpeechEnhancer()
        self._available_voices = [
            "af_heart", "af_sky", "af_bella", "af_sarah", "af_nicole",
            "am_adam", "am_michael", "bf_emma", "bf_isabella", "bm_lewis"
        ]
        
    async def initialize(self) -> bool:
        """Initialize the Kokoro engine asynchronously."""
        try:
            # Run initialization in thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self._init_engine
            )
            logger.info("Kokoro engine initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro engine: {e}")
            return False
    
    def _init_engine(self) -> None:
        """Initialize engine in executor thread."""
        self.engine = Kokoro(self.model_path, self.voices_path)
    
    def get_available_voices(self) -> List[VoiceInfo]:
        """Get list of available voices with metadata."""
        voices = []
        voice_metadata = {
            "af_heart": {"name": "Heart", "gender": "female", "description": "Warm, friendly female voice"},
            "af_sky": {"name": "Sky", "gender": "female", "description": "Clear, bright female voice"},
            "af_bella": {"name": "Bella", "gender": "female", "description": "Elegant, sophisticated female voice"},
            "af_sarah": {"name": "Sarah", "gender": "female", "description": "Professional, confident female voice"},
            "af_nicole": {"name": "Nicole", "gender": "female", "description": "Gentle, soothing female voice"},
            "am_adam": {"name": "Adam", "gender": "male", "description": "Strong, authoritative male voice"},
            "am_michael": {"name": "Michael", "gender": "male", "description": "Friendly, approachable male voice"},
            "bf_emma": {"name": "Emma", "gender": "female", "description": "Young, energetic female voice"},
            "bf_isabella": {"name": "Isabella", "gender": "female", "description": "Mature, expressive female voice"},
            "bm_lewis": {"name": "Lewis", "gender": "male", "description": "Deep, resonant male voice"},
        }
        
        for voice_id in self._available_voices:
            metadata = voice_metadata.get(voice_id, {
                "name": voice_id.replace("_", " ").title(),
                "gender": "neutral",
                "description": f"Voice {voice_id}"
            })
            
            voices.append(VoiceInfo(
                voice_id=voice_id,
                name=metadata["name"],
                language="en-us",
                gender=metadata["gender"],
                description=metadata["description"],
                sample_rate=24000,
                supported_emotions=list(VoiceEmotion),
                quality="high"
            ))
        
        return voices
    
    def _calculate_speed_adjustment(self, base_speed: float, emotion: VoiceEmotion, pacing: PacingStyle) -> float:
        """Calculate final speed based on emotion and pacing."""
        speed = base_speed
        
        # Emotion adjustments
        emotion_adjustments = {
            VoiceEmotion.EXCITED: 1.1,
            VoiceEmotion.HAPPY: 1.05,
            VoiceEmotion.CALM: 0.9,
            VoiceEmotion.SERIOUS: 0.95,
            VoiceEmotion.CASUAL: 1.0,
            VoiceEmotion.CONFIDENT: 1.0,
            VoiceEmotion.NEUTRAL: 1.0,
        }
        
        # Pacing adjustments
        pacing_adjustments = {
            PacingStyle.FAST: 1.2,
            PacingStyle.SLOW: 0.8,
            PacingStyle.CONVERSATIONAL: 1.0,
            PacingStyle.PRESENTATION: 0.9,
            PacingStyle.TUTORIAL: 0.85,
            PacingStyle.NARRATIVE: 0.95,
            PacingStyle.NATURAL: 1.0,
        }
        
        speed *= emotion_adjustments.get(emotion, 1.0)
        speed *= pacing_adjustments.get(pacing, 1.0)
        
        return max(0.25, min(3.0, speed))
    
    async def synthesize_text(self, request: TTSRequest) -> AudioSegment:
        """Synthesize text to speech with enhanced features."""
        if not self.engine:
            raise RuntimeError("Engine not initialized")
        
        # Enhance text for natural speech
        enhanced_text = self.enhancer.enhance_for_speech(request.text, request.voice_config)
        
        # Calculate final speed
        final_speed = self._calculate_speed_adjustment(
            request.voice_config.speed,
            request.voice_config.emotion,
            request.voice_config.pacing
        )
        
        try:
            # Generate audio in executor thread
            audio_data, sample_rate = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.engine.create,
                enhanced_text,
                request.voice_config.voice_id,
                final_speed
            )
            
            # Apply volume adjustment
            if request.voice_config.volume != 1.0:
                audio_data = audio_data * request.voice_config.volume
                # Prevent clipping
                audio_data = np.clip(audio_data, -1.0, 1.0)
            
            # Convert to desired format
            audio_bytes = await self._convert_audio_format(
                audio_data, sample_rate, request.output_format
            )
            
            duration = len(audio_data) / sample_rate
            
            return AudioSegment(
                audio_data=audio_bytes,
                sample_rate=sample_rate,
                duration=duration,
                format=request.output_format
            )
            
        except Exception as e:
            logger.error(f"Failed to synthesize text: {e}")
            raise
    
    async def synthesize_batch(self, texts: List[str], voice_config: VoiceConfig, 
                              output_format: AudioFormat, segment_pause: float = 0.5) -> List[AudioSegment]:
        """Synthesize multiple text segments."""
        segments = []
        
        for i, text in enumerate(texts):
            request = TTSRequest(
                text=text,
                voice_config=voice_config,
                output_format=output_format,
                streaming=False
            )
            
            segment = await self.synthesize_text(request)
            segments.append(segment)
            
            # Add pause between segments (except last one)
            if i < len(texts) - 1 and segment_pause > 0:
                pause_samples = int(segment.sample_rate * segment_pause)
                pause_data = np.zeros(pause_samples, dtype=np.float32)
                pause_bytes = await self._convert_audio_format(
                    pause_data, segment.sample_rate, output_format
                )
                
                pause_segment = AudioSegment(
                    audio_data=pause_bytes,
                    sample_rate=segment.sample_rate,
                    duration=segment_pause,
                    format=output_format
                )
                segments.append(pause_segment)
        
        return segments
    
    async def _convert_audio_format(self, audio_data: np.ndarray, sample_rate: int, 
                                   format: AudioFormat) -> bytes:
        """Convert audio data to specified format."""
        # Create temporary file for conversion
        with tempfile.NamedTemporaryFile(suffix=f".{format.value}", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            if format == AudioFormat.WAV:
                sf.write(tmp_path, audio_data, sample_rate, format='WAV')
            elif format == AudioFormat.MP3:
                # Convert via FFmpeg
                wav_path = tmp_path.replace('.mp3', '.wav')
                sf.write(wav_path, audio_data, sample_rate, format='WAV')
                await self._convert_with_ffmpeg(wav_path, tmp_path, 'mp3')
                Path(wav_path).unlink(missing_ok=True)
            elif format == AudioFormat.FLAC:
                sf.write(tmp_path, audio_data, sample_rate, format='FLAC')
            elif format == AudioFormat.OGG:
                sf.write(tmp_path, audio_data, sample_rate, format='OGG')
            
            # Read converted file
            with open(tmp_path, 'rb') as f:
                audio_bytes = f.read()
            
            return audio_bytes
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    async def _convert_with_ffmpeg(self, input_path: str, output_path: str, format: str) -> None:
        """Convert audio using FFmpeg."""
        cmd = [
            'ffmpeg', '-i', input_path, '-y',
            '-acodec', 'libmp3lame' if format == 'mp3' else format,
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed with code {process.returncode}")
    
    async def stream_synthesis(self, request: TTSRequest) -> AsyncGenerator[bytes, None]:
        """Stream audio synthesis in chunks."""
        # For now, synthesize full audio and yield in chunks
        # Future: implement true streaming synthesis
        segment = await self.synthesize_text(request)
        
        chunk_size = 4096
        audio_data = segment.audio_data
        
        for i in range(0, len(audio_data), chunk_size):
            yield audio_data[i:i + chunk_size]
            await asyncio.sleep(0.01)  # Small delay for streaming effect