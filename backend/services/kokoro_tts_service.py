import os
import subprocess
import tempfile
import soundfile as sf
import numpy as np
from pathlib import Path
import sys
import re
import uuid

from config import logger, KOKORO_DIR, BASE_DIR, AUDIO_DIR

class KokoroTTSService:
    def __init__(self):
        self.kokoro_path = KOKORO_DIR
        self.python_exec = os.environ.get("KOKORO_PYTHON", "python")
        
        # Verify Kokoro TTS installation
        if not self.kokoro_path.exists():
            logger.warning(f"Creating Kokoro TTS directory at {self.kokoro_path}")
            self.kokoro_path.mkdir(parents=True, exist_ok=True)
        
        # Check for required model files
        self.model_path = self.kokoro_path / "kokoro-v1.0.onnx"
        self.voices_path = self.kokoro_path / "voices-v1.0.bin"
        
        if not (self.model_path.exists() and self.voices_path.exists()):
            logger.error("Required model files not found!")
            logger.info("Please download the model files and place them in the kokoro-tts directory")
            raise ValueError("Missing required Kokoro TTS model files")
            
    def generate_speech(self, text, speaker_id="default", speed=1.0):
        """Generate speech using Kokoro TTS"""
        if not self.kokoro_path.exists():
            raise ValueError(f"Kokoro TTS directory not found at {self.kokoro_path}")
        
        # Validate text and speaker_id
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Ensure output directory exists
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        output_filename = f"kokoro_{uuid.uuid4()}.wav"
        output_path = AUDIO_DIR / output_filename
        
        try:
            # Confirm the script exists
            kokoro_script_path = self.kokoro_path / "kokoro-tts.py"
            if not kokoro_script_path.exists():
                raise FileNotFoundError(f"Kokoro TTS script not found at {kokoro_script_path}")
            
            # Tạo file tạm cho text đầu vào
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_input:
                tmp_input_path = tmp_input.name
                tmp_input.write(text)
            
            # Chuẩn bị command line arguments
            cmd = [
                self.python_exec,
                str(kokoro_script_path),
                tmp_input_path,
                str(output_path),
                "--voice", speaker_id
            ]
            
            # Add speed parameter if not default
            if speed != 1.0:
                cmd.extend(["--speed", str(speed)])
                
            logger.info(f"Running Kokoro TTS with command: {' '.join(map(str, cmd))}")
            logger.info(f"Working directory: {self.kokoro_path}")
            
            # Chạy tiến trình Kokoro-TTS
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=str(self.kokoro_path)  # Convert to string for Windows compatibility
            )
            stdout, stderr = process.communicate(timeout=30)  # Add timeout
            
            # Log any output for debugging
            if stdout:
                logger.info(f"Kokoro TTS stdout: {stdout}")
            if stderr:
                logger.error(f"Kokoro TTS stderr: {stderr}")
            
            # Check if output file was created
            if not output_path.exists():
                logger.error(f"Failed to create output file. Process return code: {process.returncode}")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                raise Exception(f"Failed to generate audio file. Return code: {process.returncode}")
            
            if process.returncode != 0:
                logger.error(f"Kokoro TTS process failed with return code {process.returncode}")
                raise Exception(f"Kokoro TTS failed with code {process.returncode}")
                
            # Đọc file audio đã tạo
            audio_data, sample_rate = sf.read(str(output_path))
            
            logger.info(f"Kokoro TTS generated audio successfully: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Return relative path for frontend use
            relative_path = output_path.relative_to(BASE_DIR)
            return audio_data, sample_rate, str(relative_path)
            
        except subprocess.TimeoutExpired:
            logger.error("Kokoro TTS process timed out")
            raise Exception("Audio generation timed out")
        except Exception as e:
            logger.error(f"Error in Kokoro TTS service: {str(e)}")
            raise
        finally:
            # Cleanup temporary input file
            if 'tmp_input_path' in locals() and os.path.exists(tmp_input_path):
                try:
                    os.unlink(tmp_input_path)
                except:
                    pass
                
    def get_available_speakers(self):
        """Get list of available speakers from Kokoro TTS"""
        if not self.kokoro_path.exists():
            return [{"id": "default", "name": "Default Speaker"}]
            
        try:
            # Lấy danh sách voices bằng cách chạy Kokoro TTS với tham số --help-voices
            cmd = [self.python_exec, os.path.join(self.kokoro_path, "kokoro-tts"), "--help-voices"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.kokoro_path
            )
            stdout, stderr = process.communicate()
            
            # Parse stdout để lấy danh sách voices
            voices_list = []
            voice_pattern = re.compile(r'(\d+)\.\s+(\w+)')
            
            for line in stdout.decode().splitlines():
                match = voice_pattern.search(line)
                if match:
                    voice_id = match.group(2)
                    voices_list.append({"id": voice_id, "name": f"Voice {voice_id}"})
            
            return voices_list or [{"id": "default", "name": "Default Speaker"}]
            
        except Exception as e:
            logger.error(f"Error fetching Kokoro speakers: {str(e)}")
            return [{"id": "default", "name": "Default Speaker"}]

# Khởi tạo service
kokoro_tts_service = KokoroTTSService()