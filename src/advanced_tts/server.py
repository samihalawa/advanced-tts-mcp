"""
Advanced TTS MCP Server implementation.
"""

import asyncio
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.models import Resource
from mcp.types import TextResourceContents

from .engine import KokoroEngine
from .models import (
    TTSRequest, BatchTTSRequest, VoiceConfig, AudioOutput, TTSStatus,
    VoiceEmotion, PacingStyle, AudioFormat, ServerConfig
)

logger = logging.getLogger(__name__)


class AdvancedTTSServer:
    """Advanced TTS MCP Server with enhanced features."""
    
    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the TTS server."""
        self.config = config or ServerConfig()
        self.engine = KokoroEngine(self.config.model_path, self.config.voices_path)
        self.mcp = FastMCP("Advanced TTS")
        self.active_requests: Dict[str, TTSStatus] = {}
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup MCP server
        self._setup_tools()
        self._setup_resources()
        
    def _setup_tools(self) -> None:
        """Setup MCP tools."""
        
        @self.mcp.tool()
        async def synthesize_speech(
            text: str,
            voice_id: str = "af_heart",
            speed: float = 1.0,
            emotion: str = "neutral",
            pacing: str = "natural",
            volume: float = 1.0,
            output_format: str = "wav",
            save_file: bool = False,
            filename: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Synthesize text to speech with advanced voice controls.
            
            Args:
                text: Text to convert to speech (max 10,000 characters)
                voice_id: Voice to use (af_heart, af_sky, af_bella, etc.)
                speed: Speech speed (0.25-3.0, default: 1.0)
                emotion: Voice emotion (neutral, happy, excited, calm, serious, casual, confident)
                pacing: Speech pacing (natural, conversational, presentation, tutorial, narrative, fast, slow)
                volume: Audio volume (0.1-2.0, default: 1.0)
                output_format: Audio format (wav, mp3, flac, ogg)
                save_file: Whether to save audio to file
                filename: Custom filename for saved audio
            
            Returns:
                Synthesis result with audio data and metadata
            """
            try:
                voice_config = VoiceConfig(
                    voice_id=voice_id,
                    speed=speed,
                    emotion=VoiceEmotion(emotion),
                    pacing=PacingStyle(pacing),
                    volume=volume
                )
                
                request = TTSRequest(
                    text=text,
                    voice_config=voice_config,
                    output_format=AudioFormat(output_format),
                    save_file=save_file,
                    filename=filename
                )
                
                # Update status
                self.active_requests[request.request_id] = TTSStatus(
                    request_id=request.request_id,
                    status="processing",
                    progress=0.0
                )
                
                # Synthesize audio
                segment = await self.engine.synthesize_text(request)
                
                result = {
                    "request_id": request.request_id,
                    "success": True,
                    "duration": segment.duration,
                    "sample_rate": segment.sample_rate,
                    "format": segment.format.value,
                    "audio_size": len(segment.audio_data),
                    "message": f"Successfully synthesized {len(text)} characters"
                }
                
                # Save file if requested
                if save_file:
                    filename = filename or f"tts_{request.request_id[:8]}.{output_format}"
                    file_path = self.output_dir / filename
                    
                    with open(file_path, 'wb') as f:
                        f.write(segment.audio_data)
                    
                    result["file_path"] = str(file_path)
                    result["filename"] = filename
                
                # Play audio (platform-specific)
                await self._play_audio(segment.audio_data, segment.sample_rate, output_format)
                
                # Update status
                self.active_requests[request.request_id].status = "completed"
                self.active_requests[request.request_id].progress = 1.0
                
                return result
                
            except Exception as e:
                error_msg = f"Synthesis failed: {str(e)}"
                logger.error(error_msg)
                
                if request.request_id in self.active_requests:
                    self.active_requests[request.request_id].status = "error"
                    self.active_requests[request.request_id].error = error_msg
                
                return {
                    "success": False,
                    "error": error_msg,
                    "request_id": request.request_id if 'request' in locals() else None
                }
        
        @self.mcp.tool()
        async def batch_synthesize(
            segments: List[str],
            voice_id: str = "af_heart",
            speed: float = 1.0,
            emotion: str = "neutral", 
            pacing: str = "natural",
            volume: float = 1.0,
            output_format: str = "wav",
            merge_output: bool = True,
            segment_pause: float = 0.5,
            save_file: bool = False,
            filename: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Synthesize multiple text segments with optional merging.
            
            Args:
                segments: List of text segments to synthesize
                voice_id: Voice to use for all segments
                speed: Speech speed (0.25-3.0)
                emotion: Voice emotion
                pacing: Speech pacing style
                volume: Audio volume (0.1-2.0)
                output_format: Audio format
                merge_output: Whether to merge segments into single file
                segment_pause: Pause between segments in seconds (0.0-5.0)
                save_file: Whether to save audio to file
                filename: Custom filename for saved audio
            
            Returns:
                Batch synthesis result with metadata
            """
            try:
                voice_config = VoiceConfig(
                    voice_id=voice_id,
                    speed=speed,
                    emotion=VoiceEmotion(emotion),
                    pacing=PacingStyle(pacing),
                    volume=volume
                )
                
                request = BatchTTSRequest(
                    segments=segments,
                    voice_config=voice_config,
                    output_format=AudioFormat(output_format),
                    merge_output=merge_output,
                    segment_pause=segment_pause
                )
                
                # Update status
                self.active_requests[request.batch_id] = TTSStatus(
                    request_id=request.batch_id,
                    status="processing",
                    progress=0.0
                )
                
                # Synthesize segments
                audio_segments = await self.engine.synthesize_batch(
                    segments, voice_config, AudioFormat(output_format), segment_pause
                )
                
                total_duration = sum(seg.duration for seg in audio_segments)
                total_size = sum(len(seg.audio_data) for seg in audio_segments)
                
                result = {
                    "batch_id": request.batch_id,
                    "success": True,
                    "segment_count": len(segments),
                    "total_duration": total_duration,
                    "total_size": total_size,
                    "format": output_format,
                    "merged": merge_output,
                    "message": f"Successfully synthesized {len(segments)} segments"
                }
                
                # Save files if requested
                if save_file:
                    if merge_output:
                        # Merge all segments
                        merged_audio = b''.join(seg.audio_data for seg in audio_segments)
                        filename = filename or f"batch_{request.batch_id[:8]}.{output_format}"
                        file_path = self.output_dir / filename
                        
                        with open(file_path, 'wb') as f:
                            f.write(merged_audio)
                        
                        result["file_path"] = str(file_path)
                        result["filename"] = filename
                    else:
                        # Save individual segments
                        file_paths = []
                        for i, segment in enumerate(audio_segments):
                            seg_filename = f"batch_{request.batch_id[:8]}_seg_{i+1:03d}.{output_format}"
                            file_path = self.output_dir / seg_filename
                            
                            with open(file_path, 'wb') as f:
                                f.write(segment.audio_data)
                            
                            file_paths.append(str(file_path))
                        
                        result["file_paths"] = file_paths
                        result["segment_files"] = len(file_paths)
                
                # Update status
                self.active_requests[request.batch_id].status = "completed"
                self.active_requests[request.batch_id].progress = 1.0
                
                return result
                
            except Exception as e:
                error_msg = f"Batch synthesis failed: {str(e)}"
                logger.error(error_msg)
                
                if 'request' in locals() and request.batch_id in self.active_requests:
                    self.active_requests[request.batch_id].status = "error"
                    self.active_requests[request.batch_id].error = error_msg
                
                return {
                    "success": False,
                    "error": error_msg,
                    "batch_id": request.batch_id if 'request' in locals() else None
                }
        
        @self.mcp.tool()
        async def get_voices() -> Dict[str, Any]:
            """
            Get list of available voices with their capabilities.
            
            Returns:
                List of available voices with metadata
            """
            try:
                voices = self.engine.get_available_voices()
                return {
                    "success": True,
                    "voices": [voice.dict() for voice in voices],
                    "total_voices": len(voices),
                    "supported_emotions": [e.value for e in VoiceEmotion],
                    "supported_pacing": [p.value for p in PacingStyle],
                    "supported_formats": [f.value for f in AudioFormat]
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to get voices: {str(e)}"
                }
        
        @self.mcp.tool()
        async def get_status(request_id: str) -> Dict[str, Any]:
            """
            Get processing status for a synthesis request.
            
            Args:
                request_id: Request or batch ID to check
            
            Returns:
                Current processing status
            """
            if request_id in self.active_requests:
                status = self.active_requests[request_id]
                return {
                    "success": True,
                    **status.dict()
                }
            else:
                return {
                    "success": False,
                    "error": f"Request {request_id} not found"
                }
        
        @self.mcp.tool()
        async def cancel_request(request_id: str) -> Dict[str, Any]:
            """
            Cancel a processing synthesis request.
            
            Args:
                request_id: Request or batch ID to cancel
            
            Returns:
                Cancellation result
            """
            if request_id in self.active_requests:
                self.active_requests[request_id].status = "cancelled"
                return {
                    "success": True,
                    "message": f"Request {request_id} cancelled"
                }
            else:
                return {
                    "success": False,
                    "error": f"Request {request_id} not found"
                }
        
        @self.mcp.tool()
        async def list_output_files() -> Dict[str, Any]:
            """
            List saved audio files in the output directory.
            
            Returns:
                List of saved audio files with metadata
            """
            try:
                files = []
                for file_path in self.output_dir.glob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.wav', '.mp3', '.flac', '.ogg']:
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": stat.st_size,
                            "created": stat.st_ctime,
                            "modified": stat.st_mtime,
                            "format": file_path.suffix.lower()[1:]  # Remove dot
                        })
                
                files.sort(key=lambda x: x['modified'], reverse=True)
                
                return {
                    "success": True,
                    "files": files,
                    "total_files": len(files),
                    "output_directory": str(self.output_dir)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to list files: {str(e)}"
                }
    
    def _setup_resources(self) -> None:
        """Setup MCP resources."""
        
        @self.mcp.resource("tts://voices")
        async def get_voices_resource() -> Resource:
            """Resource containing available voices information."""
            voices = self.engine.get_available_voices()
            voices_data = {
                "voices": [voice.dict() for voice in voices],
                "capabilities": {
                    "emotions": [e.value for e in VoiceEmotion],
                    "pacing_styles": [p.value for p in PacingStyle],
                    "output_formats": [f.value for f in AudioFormat],
                    "speed_range": [0.25, 3.0],
                    "volume_range": [0.1, 2.0]
                }
            }
            
            return Resource(
                uri="tts://voices",
                name="Available TTS Voices",
                description="Comprehensive list of available voices and their capabilities",
                mimeType="application/json",
                text=json.dumps(voices_data, indent=2)
            )
        
        @self.mcp.resource("tts://examples")
        async def get_examples_resource() -> Resource:
            """Resource containing usage examples."""
            examples = {
                "basic_synthesis": {
                    "description": "Basic text-to-speech synthesis",
                    "tool": "synthesize_speech",
                    "parameters": {
                        "text": "Hello, this is a basic synthesis example.",
                        "voice_id": "af_heart"
                    }
                },
                "emotional_speech": {
                    "description": "Speech with emotion and pacing",
                    "tool": "synthesize_speech", 
                    "parameters": {
                        "text": "This is exciting news! I can't wait to share it with everyone.",
                        "voice_id": "af_heart",
                        "emotion": "excited",
                        "pacing": "conversational",
                        "speed": 1.1
                    }
                },
                "tutorial_narration": {
                    "description": "Tutorial-style narration with slower pacing",
                    "tool": "synthesize_speech",
                    "parameters": {
                        "text": "Step one: Open your browser. Step two: Navigate to the website. Step three: Click the login button.",
                        "voice_id": "am_adam",
                        "emotion": "calm",
                        "pacing": "tutorial",
                        "speed": 0.9
                    }
                },
                "batch_processing": {
                    "description": "Batch synthesis of multiple segments",
                    "tool": "batch_synthesize",
                    "parameters": {
                        "segments": [
                            "Welcome to our presentation.",
                            "Today we'll cover three main topics.",
                            "Let's begin with the first topic."
                        ],
                        "voice_id": "af_sarah",
                        "emotion": "confident",
                        "pacing": "presentation",
                        "merge_output": True,
                        "segment_pause": 1.0
                    }
                }
            }
            
            return Resource(
                uri="tts://examples",
                name="TTS Usage Examples",
                description="Examples demonstrating various TTS features and use cases",
                mimeType="application/json",
                text=json.dumps(examples, indent=2)
            )
    
    async def _play_audio(self, audio_data: bytes, sample_rate: int, format: str) -> None:
        """Play audio using system audio player."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            # Play using system command (macOS/Linux)
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                cmd = ["afplay", tmp_path]
            elif system == "Linux":
                cmd = ["aplay", tmp_path] if format == "wav" else ["ffplay", "-nodisp", "-autoexit", tmp_path]
            else:  # Windows
                cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{tmp_path}').PlaySync()"]
            
            # Play asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            # Don't wait for completion, let it play in background
            asyncio.create_task(self._cleanup_after_play(process, tmp_path))
            
        except Exception as e:
            logger.warning(f"Could not play audio: {e}")
    
    async def _cleanup_after_play(self, process: asyncio.subprocess.Process, tmp_path: str) -> None:
        """Clean up temporary file after audio playback."""
        try:
            await process.wait()
            Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
    
    async def initialize(self) -> bool:
        """Initialize the TTS server."""
        success = await self.engine.initialize()
        if success:
            logger.info("Advanced TTS Server initialized successfully")
        else:
            logger.error("Failed to initialize TTS Server")
        return success
    
    def get_mcp_server(self) -> FastMCP:
        """Get the MCP server instance."""
        return self.mcp


# Main server runner
async def main():
    """Run the Advanced TTS MCP Server."""
    import sys
    import os
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = ServerConfig()
    
    # Check for model files
    if not Path(config.model_path).exists():
        logger.error(f"Model file not found: {config.model_path}")
        logger.info("Please download kokoro-v1.0.onnx and voices-v1.0.bin")
        sys.exit(1)
    
    if not Path(config.voices_path).exists():
        logger.error(f"Voices file not found: {config.voices_path}")
        logger.info("Please download kokoro-v1.0.onnx and voices-v1.0.bin")
        sys.exit(1)
    
    # Create and initialize server
    server = AdvancedTTSServer(config)
    
    if not await server.initialize():
        logger.error("Failed to initialize server")
        sys.exit(1)
    
    # Run MCP server
    mcp = server.get_mcp_server()
    await mcp.run()


if __name__ == "__main__":
    asyncio.run(main())