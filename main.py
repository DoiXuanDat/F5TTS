import logging
import time
import re
import tempfile
import soundfile as sf
import torchaudio
from cached_path import cached_path
from num2words import num2words
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
import whisper
import torch
from datetime import timedelta
import os

from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_vocoder,
    load_model,
    infer_process,
    remove_silence_for_generated_wav,
    save_spectrogram,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Log level (you can change it to DEBUG for more details)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Display logs in the standard output (console)
    ]
)

logger = logging.getLogger(__name__)

# FastAPI initialization
app = FastAPI()

# Check if the GPU decorator is available (Spaces mode)
try:
    import spaces
    USING_SPACES = True
except ImportError:
    USING_SPACES = False

def gpu_decorator(func):
    if USING_SPACES:
        return spaces.GPU(func)
    return func

# Load models
vocoder = load_vocoder()
F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
F5TTS_ema_model = load_model(
    DiT, F5TTS_model_cfg, str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
)
# Initialize Whisper model
whisper_model = whisper.load_model("base")

def generate_srt(audio_path):
    """
    Generate SRT file from audio using Whisper AI with backwards compatibility
    
    This function attempts to use the most appropriate transcription settings
    based on the installed version of Whisper, falling back to basic settings
    if advanced features aren't available.
    """
    try:
        logger.info(f"Starting transcription for audio file: {audio_path}")
        
        # First, try to detect Whisper version capabilities
        whisper_supports_word_timestamps = False
        try:
            # Attempt to create options with word_timestamps
            # This will raise an error if the feature isn't supported
            test_options = dict(
                verbose=True,
                word_timestamps=True
            )
            whisper_model.transcribe("", **test_options)
            whisper_supports_word_timestamps = True
        except TypeError:
            logger.info("Whisper version doesn't support word timestamps, using basic transcription")
        except Exception:
            # Reset any other error state
            pass

        # Configure transcription options based on available features
        transcription_options = {
            "verbose": True,
            "condition_on_previous_text": True,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0
        }
        
        # Add word timestamps only if supported
        if whisper_supports_word_timestamps:
            transcription_options["word_timestamps"] = True
        
        # Perform transcription
        logger.info("Starting Whisper transcription with options: %s", transcription_options)
        result = whisper_model.transcribe(
            audio_path,
            **transcription_options
        )
        
        # Generate SRT content
        srt_content = []
        for i, segment in enumerate(result["segments"], 1):
            # Convert timestamps to millisecond precision
            start_time = segment["start"]
            end_time = segment["end"]
            
            # Format timestamps
            start = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d},{int((start_time*1000)%1000):03d}"
            end = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d},{int((end_time*1000)%1000):03d}"
            
            text = segment["text"].strip()
            
            # Add word-level timing information if available
            if whisper_supports_word_timestamps and "words" in segment:
                text_with_timing = []
                for word in segment["words"]:
                    word_text = word["word"]
                    text_with_timing.append(f"{word_text}")
                text = " ".join(text_with_timing)
            
            srt_content.extend([
                str(i),
                f"{start} --> {end}",
                text + "\n",
                ""
            ])
        
        # Save to file
        srt_path = audio_path.rsplit(".", 1)[0] + ".srt"
        logger.info(f"Writing SRT file to: {srt_path}")
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
            
        logger.info("SRT file generated successfully")
        return srt_path
        
    except Exception as e:
        logger.error(f"Error in generate_srt: {str(e)}", exc_info=True)
        raise Exception(f"Failed to generate SRT: {str(e)}")

def validate_timestamps(segments):
    """
    Validate and adjust timestamps to ensure they are sequential and have no gaps
    """
    adjusted_segments = []
    previous_end = 0
    
    for segment in segments:
        start_time = max(segment["start"], previous_end)
        end_time = max(start_time + 0.001, segment["end"])  # Ensure minimum duration
        
        adjusted_segment = segment.copy()
        adjusted_segment["start"] = start_time
        adjusted_segment["end"] = end_time
        
        adjusted_segments.append(adjusted_segment)
        previous_end = end_time
        
    return adjusted_segments

# Function to translate numbers to text
def translate_number_to_text(text):
    text_separated = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text_separated = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text_separated)

    def replace_number(match):
        number = match.group()
        return num2words(int(number), lang='en')  # Keep En language here

    return re.sub(r'\b\d+\b', replace_number, text_separated)

@gpu_decorator
def infer(
    ref_audio_orig, ref_text, gen_text, remove_silence=False, cross_fade_duration=0.15, speed=1.0
):
    logger.info("Starting text preprocessing...")
    gen_text = gen_text.lower()
    gen_text = translate_number_to_text(gen_text)

    # Inference process
    final_wave, final_sample_rate, combined_spectrogram = infer_process(
        ref_audio_orig, ref_text, gen_text, F5TTS_ema_model, vocoder,
        cross_fade_duration=cross_fade_duration, speed=speed
    )

    # Remove silence if necessary
    if remove_silence:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wave:
            sf.write(tmp_wave.name, final_wave, final_sample_rate)
            remove_silence_for_generated_wav(tmp_wave.name)
            final_wave, _ = torchaudio.load(tmp_wave.name)
        final_wave = final_wave.squeeze().cpu().numpy()

    # Save the spectrogram temporarily
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_spectrogram:
        spectrogram_path = tmp_spectrogram.name
        save_spectrogram(combined_spectrogram, spectrogram_path)

    logger.info("Inference completed successfully.")
    return final_wave, final_sample_rate, spectrogram_path

# Endpoint for audio generation
@app.post("/generate-audio/")
async def generate_audio(
    ref_audio: UploadFile = File(...),
    ref_text: str = Form(...),
    gen_text: str = Form(...),
    remove_silence: bool = False,
    cross_fade_duration: float = 0.15,
    speed: float = 1.0
):
    start_time = time.time()
    try:
        # Input file validation
        if not ref_audio.filename.endswith(".wav"):
            raise HTTPException(status_code=400, detail="The audio file must be in WAV format.")

        # Save the audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(ref_audio.file.read())
            ref_audio_path = tmp_audio.name

        # Input text validation
        if not ref_text or not gen_text:
            raise HTTPException(status_code=400, detail="Both reference and generation texts are required.")

        # Generate audio
        final_wave, final_sample_rate, _ = infer(
            ref_audio_path, ref_text, gen_text, remove_silence, cross_fade_duration, speed
        )

        # Save generated audio
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"generated_audio_{int(time.time())}.wav"
        output_path = os.path.join(output_dir, output_filename)
        sf.write(output_path, final_wave, final_sample_rate)

        execution_time = time.time() - start_time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")

        # Return both the full path and filename
        return {
            "status": "success",
            "filename": output_filename,
            "full_path": output_path,
            "execution_time": execution_time
        }

    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-srt/")
async def generate_srt_endpoint(audio_path: str = Form(...)):
    """
    Endpoint to generate SRT file from an audio file
    """
    try:
        logger.info(f"Received request to generate SRT for audio: {audio_path}")
        
        if not audio_path:
            logger.error("No audio path provided")
            raise HTTPException(status_code=400, detail="Audio path is required")
            
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found at path: {audio_path}")
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found at path: {audio_path}"
            )
            
        logger.info("Generating SRT file...")
        try:
            srt_path = generate_srt(audio_path)
            logger.info(f"SRT file generated successfully at: {srt_path}")
        except Exception as e:
            logger.error(f"Error in generate_srt: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate SRT: {str(e)}"
            )
            
        if not os.path.exists(srt_path):
            logger.error("SRT file was not created")
            raise HTTPException(
                status_code=500,
                detail="SRT file was not created"
            )
            
        logger.info("Sending SRT file response")
        return FileResponse(
            path=srt_path,
            filename=os.path.basename(srt_path),
            media_type="text/srt"
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in generate_srt_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-audio-with-ref-audio/")
async def generate_audio_with_local_ref_audio(
    gen_text: str = "",
    remove_silence: bool = False,
    cross_fade_duration: float = 0.15,
    speed: float = 1.0
):
    """
    Generates audio using a local reference audio file and a generation text.
    """
    start_time = time.time()  # Start the timer
    try:
        # Path to the local reference audio file
        ref_audio_path = "./tts_voice_files/final.wav"
        ref_text = "The checkpoints currently support English and Chinese. If you're having issues, try converting your reference audio to WAV or MP3, clipping it to 15s with cutting in the bottom right corner (otherwise might have non-optimal auto-trimmed result). NOTE: Reference text will be automatically transcribed with Whisper if not provided. For best results, keep your reference clips short (<15s). Ensure the audio is fully uploaded before generating"  # Fixed reference text

        # Check that the reference file exists
        if not os.path.exists(ref_audio_path):
            raise HTTPException(status_code=404, detail="The reference audio file does not exist.")

        # Generation text validation
        if not gen_text:
            raise HTTPException(status_code=400, detail="The generation text is required.")

        # Perform inference
        logger.info("Starting audio inference...")
        final_wave, final_sample_rate, _ = infer(
            ref_audio_path, ref_text, gen_text, remove_silence, cross_fade_duration, speed
        )

        # Output path for the generated audio
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        generated_audio_path = os.path.join(output_dir, "generated_audio.wav")
        sf.write(generated_audio_path, final_wave, final__sample_rate)

        execution_time = time.time() - start_time  # Calculate total time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")

        return FileResponse(
            path=generated_audio_path,
            filename="generated_audio.wav",
            media_type="audio/wav"
        )

    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=5)