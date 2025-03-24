# backend/services/kokoro_tts_service.py
import os
import subprocess
import tempfile
import soundfile as sf
import numpy as np
from pathlib import Path
import sys
from config import logger, BASE_DIR
import re

class KokoroTTSService:
    def __init__(self):
        # Đường dẫn đến thư mục cài đặt Kokoro-TTS
        self.kokoro_path = os.environ.get("KOKORO_TTS_PATH", str(BASE_DIR / "kokoro-tts"))
        self.python_exec = os.environ.get("KOKORO_PYTHON", "python")
        
        # Kiểm tra sự tồn tại của Kokoro-TTS
        if not os.path.exists(self.kokoro_path):
            logger.warning(f"Kokoro TTS not found at {self.kokoro_path}")
        else:
            logger.info(f"Kokoro TTS found at {self.kokoro_path}")
            
    def generate_speech(self, text, speaker_id="default", speed=1.0):
        """Generate speech using Kokoro TTS"""
        if not os.path.exists(self.kokoro_path):
            raise ValueError(f"Kokoro TTS not found at {self.kokoro_path}")
            
        # Tạo file tạm để lưu output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_output:
            output_path = tmp_output.name
            
        try:
            # Tạo file tạm cho text đầu vào
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_input:
                tmp_input_path = tmp_input.name
                tmp_input.write(text)
            
            # Chuẩn bị command line arguments
            cmd = [
                self.python_exec,
                os.path.join(self.kokoro_path, "kokoro-tts"),
                tmp_input_path,
                output_path,
                "--voice", speaker_id
            ]
            
            if speed != 1.0:
                cmd.extend(["--speed", str(speed)])
                
            logger.info(f"Running Kokoro TTS with command: {' '.join(cmd)}")
            
            # Chạy tiến trình Kokoro-TTS
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                cwd=self.kokoro_path
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Kokoro TTS error: {stderr.decode()}")
                raise Exception(f"Kokoro TTS failed with code {process.returncode}: {stderr.decode()}")
                
            # Đọc file audio đã tạo
            audio_data, sample_rate = sf.read(output_path)
            
            logger.info(f"Kokoro TTS generated audio successfully: {len(audio_data)} samples at {sample_rate}Hz")
            return audio_data, sample_rate
            
        except Exception as e:
            logger.error(f"Error in Kokoro TTS service: {str(e)}")
            raise
        finally:
            # Xóa file tạm nếu tồn tại
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
            
            if 'tmp_input_path' in locals() and os.path.exists(tmp_input_path):
                try:
                    os.unlink(tmp_input_path)
                except:
                    pass
                
    def get_available_speakers(self):
        """Get list of available speakers from Kokoro TTS"""
        if not os.path.exists(self.kokoro_path):
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