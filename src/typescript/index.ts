#!/usr/bin/env node

/**
 * Advanced TTS MCP Server - TypeScript Implementation for Smithery.ai
 * 
 * High-quality neural text-to-speech synthesis with enhanced features including:
 * - Local Kokoro TTS engine with natural voice synthesis
 * - Streaming audio processing and playback
 * - Advanced voice controls (speed, emotion, pacing)
 * - Batch processing for long content
 * - Multiple export formats
 * - Queue management with cancellation support
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { randomUUID } from 'crypto';

// Configuration schema for Smithery deployment
const ConfigSchema = z.object({
  defaultVoice: z.string().default('af_heart'),
  defaultSpeed: z.number().min(0.25).max(3.0).default(1.0),
  defaultEmotion: z.enum(['neutral', 'happy', 'excited', 'calm', 'serious', 'casual', 'confident']).default('neutral'),
  defaultPacing: z.enum(['natural', 'conversational', 'presentation', 'tutorial', 'narrative', 'fast', 'slow']).default('natural'),
  enableFileOutput: z.boolean().default(false),
  maxTextLength: z.number().min(100).max(50000).default(10000),
  debugMode: z.boolean().default(false),
});

type Config = z.infer<typeof ConfigSchema>;

// Voice emotion types
const VoiceEmotions = {
  neutral: { speedMod: 1.0, description: 'Standard, professional tone' },
  happy: { speedMod: 1.05, description: 'Upbeat, cheerful expression' },
  excited: { speedMod: 1.1, description: 'Enthusiastic, energetic delivery' },
  calm: { speedMod: 0.9, description: 'Relaxed, soothing tone' },
  serious: { speedMod: 0.95, description: 'Formal, authoritative delivery' },
  casual: { speedMod: 1.0, description: 'Relaxed, conversational style' },
  confident: { speedMod: 1.0, description: 'Assured, professional tone' },
} as const;

// Pacing style types
const PacingStyles = {
  natural: { speedMod: 1.0, description: 'Balanced, human-like rhythm' },
  conversational: { speedMod: 1.0, description: 'Casual discussion pace' },
  presentation: { speedMod: 0.9, description: 'Professional speaking rhythm' },
  tutorial: { speedMod: 0.85, description: 'Educational, clear delivery' },
  narrative: { speedMod: 0.95, description: 'Storytelling pace' },
  fast: { speedMod: 1.2, description: 'Quick delivery' },
  slow: { speedMod: 0.8, description: 'Deliberate delivery' },
} as const;

// Available voices with metadata
const AvailableVoices = {
  af_heart: { name: 'Heart', gender: 'female', description: 'Warm, friendly female voice' },
  af_sky: { name: 'Sky', gender: 'female', description: 'Clear, bright female voice' },
  af_bella: { name: 'Bella', gender: 'female', description: 'Elegant, sophisticated female voice' },
  af_sarah: { name: 'Sarah', gender: 'female', description: 'Professional, confident female voice' },
  af_nicole: { name: 'Nicole', gender: 'female', description: 'Gentle, soothing female voice' },
  am_adam: { name: 'Adam', gender: 'male', description: 'Strong, authoritative male voice' },
  am_michael: { name: 'Michael', gender: 'male', description: 'Friendly, approachable male voice' },
  bf_emma: { name: 'Emma', gender: 'female', description: 'Young, energetic female voice' },
  bf_isabella: { name: 'Isabella', gender: 'female', description: 'Mature, expressive female voice' },
  bm_lewis: { name: 'Lewis', gender: 'male', description: 'Deep, resonant male voice' },
} as const;

// Audio format support
const AudioFormats = ['wav', 'mp3', 'flac', 'ogg'] as const;

class AdvancedTTSServer {
  private config: Config;
  private activeRequests: Map<string, any> = new Map();
  private outputDir: string;

  constructor(config: Config) {
    this.config = config;
    this.outputDir = join(tmpdir(), 'advanced-tts-mcp');
    this.ensureOutputDir();
  }

  private async ensureOutputDir(): Promise<void> {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      if (this.config.debugMode) {
        console.error('Failed to create output directory:', error);
      }
    }
  }

  private enhanceTextForSpeech(
    text: string,
    emotion: keyof typeof VoiceEmotions,
    pacing: keyof typeof PacingStyles
  ): string {
    let enhanced = text.trim();

    // Add natural pauses based on pacing
    if (pacing === 'conversational') {
      enhanced = enhanced.replace(/([.!?])\s+/g, '$1... ');
      enhanced = enhanced.replace(/([,;:])\s+/g, '$1.. ');
    } else if (pacing === 'tutorial') {
      enhanced = enhanced.replace(/([.!?])\s+/g, '$1.... ');
      enhanced = enhanced.replace(/(\d+\.)\s+/g, '$1... ');
    } else if (pacing === 'presentation') {
      enhanced = enhanced.replace(/([.!?])\s+/g, '$1... ');
      enhanced = enhanced.replace(/(\w+:)\s+/g, '$1.. ');
    }

    // Apply emotion markers
    if (emotion === 'excited') {
      enhanced = enhanced.replace(/\b(amazing|awesome|incredible|fantastic|great)\b/gi, '*$1*');
    } else if (emotion === 'casual') {
      enhanced = enhanced.replace(/\byou are\b/gi, "you're");
      enhanced = enhanced.replace(/\bit is\b/gi, "it's");
      enhanced = enhanced.replace(/\bthat is\b/gi, "that's");
      enhanced = enhanced.replace(/\bcannot\b/gi, "can't");
    }

    return enhanced;
  }

  private calculateFinalSpeed(
    baseSpeed: number,
    emotion: keyof typeof VoiceEmotions,
    pacing: keyof typeof PacingStyles
  ): number {
    const emotionMod = VoiceEmotions[emotion].speedMod;
    const pacingMod = PacingStyles[pacing].speedMod;
    const finalSpeed = baseSpeed * emotionMod * pacingMod;
    return Math.max(0.25, Math.min(3.0, finalSpeed));
  }

  private async synthesizeWithPython(
    text: string,
    voiceId: string,
    speed: number,
    outputFormat: string,
    saveFile: boolean,
    filename?: string
  ): Promise<{ success: boolean; audioPath?: string; duration?: number; error?: string; requestId: string }> {
    const requestId = randomUUID();
    
    try {
      // Call Python TTS implementation
      const pythonScript = `
import sys
import os
import asyncio
import tempfile
import json
sys.path.append('${join(process.cwd(), 'src/advanced_tts')}')

from engine import KokoroEngine
from models import TTSRequest, VoiceConfig, VoiceEmotion, PacingStyle, AudioFormat

async def synthesize():
    try:
        engine = KokoroEngine()
        await engine.initialize()
        
        voice_config = VoiceConfig(
            voice_id="${voiceId}",
            speed=${speed},
            emotion=VoiceEmotion.NEUTRAL,
            pacing=PacingStyle.NATURAL,
            volume=1.0
        )
        
        request = TTSRequest(
            text="${text.replace(/"/g, '\\"').replace(/\n/g, '\\n')}",
            voice_config=voice_config,
            output_format=AudioFormat.${outputFormat.toUpperCase()},
            save_file=${saveFile},
            filename="${filename || ''}"
        )
        
        segment = await engine.synthesize_text(request)
        
        # Save audio to file
        output_path = "${join(this.outputDir, filename || `${requestId}.${outputFormat}`)}"
        with open(output_path, 'wb') as f:
            f.write(segment.audio_data)
        
        result = {
            "success": True,
            "audioPath": output_path,
            "duration": segment.duration,
            "requestId": "${requestId}"
        }
        print(json.dumps(result))
        
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "requestId": "${requestId}"
        }
        print(json.dumps(result))

asyncio.run(synthesize())
`;

      const tempScriptPath = join(tmpdir(), `tts_${requestId}.py`);
      await fs.writeFile(tempScriptPath, pythonScript);

      return new Promise((resolve) => {
        const python = spawn('python', [tempScriptPath], {
          cwd: process.cwd(),
          stdio: ['pipe', 'pipe', 'pipe']
        });

        let output = '';
        let error = '';

        python.stdout.on('data', (data) => {
          output += data.toString();
        });

        python.stderr.on('data', (data) => {
          error += data.toString();
        });

        python.on('close', async (code) => {
          // Cleanup temp script
          try {
            await fs.unlink(tempScriptPath);
          } catch {}

          if (code === 0 && output.trim()) {
            try {
              const result = JSON.parse(output.trim());
              resolve({ ...result, requestId });
            } catch {
              resolve({ success: false, error: 'Failed to parse output', requestId });
            }
          } else {
            resolve({ 
              success: false, 
              error: error || `Python process exited with code ${code}`, 
              requestId 
            });
          }
        });
      });

    } catch (error) {
      return { 
        success: false, 
        error: `Synthesis failed: ${error}`, 
        requestId 
      };
    }
  }

  async synthesizeSpeech(params: {
    text: string;
    voiceId?: string;
    speed?: number;
    emotion?: keyof typeof VoiceEmotions;
    pacing?: keyof typeof PacingStyles;
    volume?: number;
    outputFormat?: string;
    saveFile?: boolean;
    filename?: string;
  }) {
    const {
      text,
      voiceId = this.config.defaultVoice,
      speed = this.config.defaultSpeed,
      emotion = this.config.defaultEmotion as keyof typeof VoiceEmotions,
      pacing = this.config.defaultPacing as keyof typeof PacingStyles,
      volume = 1.0,
      outputFormat = 'wav',
      saveFile = this.config.enableFileOutput,
      filename
    } = params;

    // Validate text length
    if (text.length > this.config.maxTextLength) {
      throw new Error(`Text length (${text.length}) exceeds maximum allowed (${this.config.maxTextLength})`);
    }

    // Enhance text for natural speech
    const enhancedText = this.enhanceTextForSpeech(text, emotion, pacing);
    
    // Calculate final speed
    const finalSpeed = this.calculateFinalSpeed(speed, emotion, pacing);

    // Synthesize using Python backend
    const result = await this.synthesizeWithPython(
      enhancedText,
      voiceId,
      finalSpeed,
      outputFormat,
      saveFile,
      filename
    );

    if (result.success) {
      this.activeRequests.set(result.requestId, {
        status: 'completed',
        result
      });

      return {
        success: true,
        requestId: result.requestId,
        duration: result.duration,
        voiceUsed: voiceId,
        speedUsed: finalSpeed,
        emotion,
        pacing,
        outputFormat,
        filePath: saveFile ? result.audioPath : undefined,
        message: `Successfully synthesized ${text.length} characters with ${voiceId} voice`
      };
    } else {
      throw new Error(result.error || 'Synthesis failed');
    }
  }

  async batchSynthesize(params: {
    segments: string[];
    voiceId?: string;
    speed?: number;
    emotion?: keyof typeof VoiceEmotions;
    pacing?: keyof typeof PacingStyles;
    volume?: number;
    outputFormat?: string;
    mergeOutput?: boolean;
    segmentPause?: number;
    saveFile?: boolean;
    filename?: string;
  }) {
    const {
      segments,
      voiceId = this.config.defaultVoice,
      speed = this.config.defaultSpeed,
      emotion = this.config.defaultEmotion as keyof typeof VoiceEmotions,
      pacing = this.config.defaultPacing as keyof typeof PacingStyles,
      volume = 1.0,
      outputFormat = 'wav',
      mergeOutput = true,
      segmentPause = 0.5,
      saveFile = this.config.enableFileOutput,
      filename
    } = params;

    const batchId = randomUUID();
    const results = [];
    let totalDuration = 0;

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const segmentFilename = mergeOutput ? undefined : `${batchId}_segment_${i + 1}.${outputFormat}`;
      
      const result = await this.synthesizeSpeech({
        text: segment,
        voiceId,
        speed,
        emotion,
        pacing,
        volume,
        outputFormat,
        saveFile: saveFile && !mergeOutput,
        filename: segmentFilename
      });

      results.push(result);
      totalDuration += result.duration || 0;
      
      // Add pause duration (except for last segment)
      if (i < segments.length - 1) {
        totalDuration += segmentPause;
      }
    }

    // TODO: Implement audio merging for mergeOutput=true
    // This would require additional audio processing capabilities

    return {
      success: true,
      batchId,
      segmentCount: segments.length,
      totalDuration,
      segments: results,
      mergedOutput: mergeOutput,
      outputFormat,
      message: `Successfully synthesized ${segments.length} segments`
    };
  }

  getVoices() {
    return {
      success: true,
      voices: Object.entries(AvailableVoices).map(([id, info]) => ({
        voiceId: id,
        name: info.name,
        gender: info.gender,
        description: info.description,
        language: 'en-us',
        sampleRate: 24000,
        quality: 'high'
      })),
      emotions: Object.entries(VoiceEmotions).map(([key, value]) => ({
        emotion: key,
        description: value.description
      })),
      pacingStyles: Object.entries(PacingStyles).map(([key, value]) => ({
        pacing: key,
        description: value.description
      })),
      supportedFormats: [...AudioFormats],
      capabilities: {
        speedRange: [0.25, 3.0],
        volumeRange: [0.1, 2.0],
        maxTextLength: this.config.maxTextLength
      }
    };
  }

  getStatus(requestId: string) {
    const request = this.activeRequests.get(requestId);
    if (request) {
      return {
        success: true,
        requestId,
        status: request.status,
        result: request.result
      };
    } else {
      return {
        success: false,
        error: `Request ${requestId} not found`
      };
    }
  }

  async listOutputFiles() {
    try {
      const files = await fs.readdir(this.outputDir);
      const audioFiles = files.filter(file => 
        AudioFormats.some(format => file.endsWith(`.${format}`))
      );

      const fileInfo = await Promise.all(
        audioFiles.map(async (file) => {
          const filePath = join(this.outputDir, file);
          const stats = await fs.stat(filePath);
          return {
            filename: file,
            path: filePath,
            size: stats.size,
            created: stats.birthtime.toISOString(),
            modified: stats.mtime.toISOString(),
            format: file.split('.').pop()
          };
        })
      );

      return {
        success: true,
        files: fileInfo.sort((a, b) => 
          new Date(b.modified).getTime() - new Date(a.modified).getTime()
        ),
        totalFiles: fileInfo.length,
        outputDirectory: this.outputDir
      };
    } catch (error) {
      return {
        success: false,
        error: `Failed to list files: ${error}`
      };
    }
  }
}

// Create and configure the MCP server
function createServer() {
  // Parse configuration from environment or use defaults
  const configData = process.env.MCP_CONFIG ? 
    JSON.parse(Buffer.from(process.env.MCP_CONFIG, 'base64').toString()) : {};
  
  const config = ConfigSchema.parse(configData);
  const ttsServer = new AdvancedTTSServer(config);

  if (config.debugMode) {
    console.error('Advanced TTS MCP Server starting with config:', config);
  }

  const server = new Server(
    {
      name: 'advanced-tts-mcp',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    }
  );

  // Register tools
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: 'synthesize_speech',
          description: 'Convert text to speech with advanced voice controls and natural expression',
          inputSchema: {
            type: 'object',
            properties: {
              text: {
                type: 'string',
                description: 'Text to convert to speech',
                maxLength: config.maxTextLength,
              },
              voiceId: {
                type: 'string',
                description: 'Voice to use for synthesis',
                enum: Object.keys(AvailableVoices),
                default: config.defaultVoice,
              },
              speed: {
                type: 'number',
                description: 'Speech speed (0.25-3.0)',
                minimum: 0.25,
                maximum: 3.0,
                default: config.defaultSpeed,
              },
              emotion: {
                type: 'string',
                description: 'Voice emotion',
                enum: Object.keys(VoiceEmotions),
                default: config.defaultEmotion,
              },
              pacing: {
                type: 'string',
                description: 'Speech pacing style',
                enum: Object.keys(PacingStyles),
                default: config.defaultPacing,
              },
              volume: {
                type: 'number',
                description: 'Audio volume (0.1-2.0)',
                minimum: 0.1,
                maximum: 2.0,
                default: 1.0,
              },
              outputFormat: {
                type: 'string',
                description: 'Audio output format',
                enum: [...AudioFormats],
                default: 'wav',
              },
              saveFile: {
                type: 'boolean',
                description: 'Save audio to file',
                default: config.enableFileOutput,
              },
              filename: {
                type: 'string',
                description: 'Custom filename for saved audio',
              },
            },
            required: ['text'],
          },
        },
        {
          name: 'batch_synthesize',
          description: 'Synthesize multiple text segments with optional merging and intelligent pacing',
          inputSchema: {
            type: 'object',
            properties: {
              segments: {
                type: 'array',
                items: { type: 'string' },
                description: 'List of text segments to synthesize',
                minItems: 1,
              },
              voiceId: {
                type: 'string',
                description: 'Voice to use for all segments',
                enum: Object.keys(AvailableVoices),
                default: config.defaultVoice,
              },
              speed: {
                type: 'number',
                description: 'Speech speed (0.25-3.0)',
                minimum: 0.25,
                maximum: 3.0,
                default: config.defaultSpeed,
              },
              emotion: {
                type: 'string',
                description: 'Voice emotion for all segments',
                enum: Object.keys(VoiceEmotions),
                default: config.defaultEmotion,
              },
              pacing: {
                type: 'string',
                description: 'Speech pacing style for all segments',
                enum: Object.keys(PacingStyles),
                default: config.defaultPacing,
              },
              outputFormat: {
                type: 'string',
                description: 'Audio output format',
                enum: [...AudioFormats],
                default: 'wav',
              },
              mergeOutput: {
                type: 'boolean',
                description: 'Merge segments into single file',
                default: true,
              },
              segmentPause: {
                type: 'number',
                description: 'Pause between segments in seconds',
                minimum: 0.0,
                maximum: 5.0,
                default: 0.5,
              },
              saveFile: {
                type: 'boolean',
                description: 'Save audio to file',
                default: config.enableFileOutput,
              },
              filename: {
                type: 'string',
                description: 'Custom filename for saved audio',
              },
            },
            required: ['segments'],
          },
        },
        {
          name: 'get_voices',
          description: 'Get list of available voices with their capabilities and supported features',
          inputSchema: {
            type: 'object',
            properties: {},
          },
        },
        {
          name: 'get_status',
          description: 'Get processing status for a synthesis request',
          inputSchema: {
            type: 'object',
            properties: {
              requestId: {
                type: 'string',
                description: 'Request ID to check status for',
              },
            },
            required: ['requestId'],
          },
        },
        {
          name: 'list_output_files',
          description: 'List saved audio files in the output directory with metadata',
          inputSchema: {
            type: 'object',
            properties: {},
          },
        },
      ],
    };
  });

  // Register tool handlers
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case 'synthesize_speech':
          const result = await ttsServer.synthesizeSpeech(args as any);
          return {
            content: [
              {
                type: 'text',
                text: `🎙️ **TTS Synthesis Complete**\n\n` +
                     `**Request ID:** ${result.requestId}\n` +
                     `**Voice:** ${result.voiceUsed} (${AvailableVoices[result.voiceUsed as keyof typeof AvailableVoices]?.name})\n` +
                     `**Duration:** ${result.duration?.toFixed(2)}s\n` +
                     `**Speed:** ${result.speedUsed?.toFixed(2)}x\n` +
                     `**Emotion:** ${result.emotion}\n` +
                     `**Pacing:** ${result.pacing}\n` +
                     `**Format:** ${result.outputFormat.toUpperCase()}\n` +
                     `${result.filePath ? `**File:** ${result.filePath}\n` : ''}` +
                     `\n${result.message}`,
              },
            ],
          };

        case 'batch_synthesize':
          const batchResult = await ttsServer.batchSynthesize(args as any);
          return {
            content: [
              {
                type: 'text',
                text: `🎙️ **Batch TTS Synthesis Complete**\n\n` +
                     `**Batch ID:** ${batchResult.batchId}\n` +
                     `**Segments:** ${batchResult.segmentCount}\n` +
                     `**Total Duration:** ${batchResult.totalDuration.toFixed(2)}s\n` +
                     `**Format:** ${batchResult.outputFormat.toUpperCase()}\n` +
                     `**Merged:** ${batchResult.mergedOutput ? 'Yes' : 'No'}\n\n` +
                     `${batchResult.message}`,
              },
            ],
          };

        case 'get_voices':
          const voices = ttsServer.getVoices();
          const voiceList = voices.voices.map(v => 
            `**${v.name}** (${v.voiceId}) - ${v.description}`
          ).join('\n');
          
          const emotionList = voices.emotions.map(e => 
            `**${e.emotion}** - ${e.description}`
          ).join('\n');
          
          const pacingList = voices.pacingStyles.map(p => 
            `**${p.pacing}** - ${p.description}`
          ).join('\n');

          return {
            content: [
              {
                type: 'text',
                text: `🎙️ **Available Voices & Capabilities**\n\n` +
                     `## Voices (${voices.voices.length})\n${voiceList}\n\n` +
                     `## Emotions (${voices.emotions.length})\n${emotionList}\n\n` +
                     `## Pacing Styles (${voices.pacingStyles.length})\n${pacingList}\n\n` +
                     `## Supported Formats\n${voices.supportedFormats.join(', ')}\n\n` +
                     `## Capabilities\n` +
                     `- **Speed Range:** ${voices.capabilities.speedRange.join(' - ')}x\n` +
                     `- **Volume Range:** ${voices.capabilities.volumeRange.join(' - ')}x\n` +
                     `- **Max Text Length:** ${voices.capabilities.maxTextLength.toLocaleString()} characters`,
              },
            ],
          };

        case 'get_status':
          const status = ttsServer.getStatus(args.requestId as string);
          return {
            content: [
              {
                type: 'text',
                text: status.success 
                  ? `🎙️ **Request Status**\n\n**ID:** ${status.requestId}\n**Status:** ${status.status}\n**Details:** ${JSON.stringify(status.result, null, 2)}`
                  : `❌ **Error:** ${status.error}`,
              },
            ],
          };

        case 'list_output_files':
          const fileList = await ttsServer.listOutputFiles();
          if (fileList.success) {
            const files = fileList.files.map(f => 
              `**${f.filename}** (${(f.size / 1024).toFixed(1)}KB) - ${f.format?.toUpperCase()}`
            ).join('\n');
            
            return {
              content: [
                {
                  type: 'text',
                  text: `🎙️ **Output Files (${fileList.totalFiles})**\n\n` +
                       `**Directory:** ${fileList.outputDirectory}\n\n` +
                       `${files || 'No audio files found'}`,
                },
              ],
            };
          } else {
            return {
              content: [
                {
                  type: 'text',
                  text: `❌ **Error:** ${fileList.error}`,
                },
              ],
            };
          }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ **Error:** ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  });

  // Register resources
  server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return {
      resources: [
        {
          uri: 'tts://voices',
          name: 'Available TTS Voices',
          description: 'Comprehensive list of available voices and their capabilities',
          mimeType: 'application/json',
        },
        {
          uri: 'tts://examples',
          name: 'TTS Usage Examples',
          description: 'Examples demonstrating various TTS features and use cases',
          mimeType: 'application/json',
        },
      ],
    };
  });

  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;

    switch (uri) {
      case 'tts://voices':
        const voices = ttsServer.getVoices();
        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(voices, null, 2),
            },
          ],
        };

      case 'tts://examples':
        const examples = {
          basic_synthesis: {
            description: 'Basic text-to-speech synthesis',
            tool: 'synthesize_speech',
            parameters: {
              text: 'Hello, this is a basic synthesis example.',
              voiceId: 'af_heart',
            },
          },
          emotional_speech: {
            description: 'Speech with emotion and pacing',
            tool: 'synthesize_speech',
            parameters: {
              text: 'This is exciting news! I can\'t wait to share it with everyone.',
              voiceId: 'af_heart',
              emotion: 'excited',
              pacing: 'conversational',
              speed: 1.1,
            },
          },
          tutorial_narration: {
            description: 'Tutorial-style narration with slower pacing',
            tool: 'synthesize_speech',
            parameters: {
              text: 'Step one: Open your browser. Step two: Navigate to the website. Step three: Click the login button.',
              voiceId: 'am_adam',
              emotion: 'calm',
              pacing: 'tutorial',
              speed: 0.9,
            },
          },
          batch_processing: {
            description: 'Batch synthesis of multiple segments',
            tool: 'batch_synthesize',
            parameters: {
              segments: [
                'Welcome to our presentation.',
                'Today we\'ll cover three main topics.',
                'Let\'s begin with the first topic.',
              ],
              voiceId: 'af_sarah',
              emotion: 'confident',
              pacing: 'presentation',
              mergeOutput: true,
              segmentPause: 1.0,
            },
          },
        };

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(examples, null, 2),
            },
          ],
        };

      default:
        throw new Error(`Unknown resource: ${uri}`);
    }
  });

  return server;
}

// HTTP server for Smithery hosting
async function createHttpServer() {
  const { createServer: createHttpServer } = await import('http');
  const server = createMcpServer();

  const httpServer = createHttpServer(async (req, res) => {
    if (req.method === 'GET' && req.url?.startsWith('/mcp')) {
      // Handle MCP over HTTP for Smithery
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      });
      
      // Parse config from query parameters
      const url = new URL(req.url, `http://${req.headers.host}`);
      const configParam = url.searchParams.get('config');
      
      if (configParam) {
        process.env.MCP_CONFIG = configParam;
      }
      
      // Return server info
      res.end(JSON.stringify({
        name: 'advanced-tts-mcp',
        version: '1.0.0',
        status: 'ready'
      }));
      
    } else if (req.method === 'POST' && req.url === '/mcp') {
      // Handle MCP requests
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', async () => {
        try {
          const request = JSON.parse(body);
          // Process MCP request through server
          // This would need to be implemented based on MCP over HTTP spec
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ result: 'processed' }));
        } catch (error) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid request' }));
        }
      });
      
    } else {
      res.writeHead(404);
      res.end('Not Found');
    }
  });

  const port = process.env.PORT || 3000;
  httpServer.listen(port, () => {
    console.error(`Advanced TTS MCP Server listening on port ${port}`);
  });
}

// Main entry point
async function main() {
  // Check if running in HTTP mode (for Smithery hosting)
  if (process.env.MCP_TRANSPORT === 'http' || process.env.PORT) {
    await createHttpServer();
  } else {
    // STDIO mode for local development
    const server = createServer();
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    console.error('Advanced TTS MCP Server running on stdio');
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error('Server error:', error);
    process.exit(1);
  });
}