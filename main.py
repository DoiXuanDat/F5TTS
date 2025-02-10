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
    """
    Generates audio with an F5-TTS model.
    """
    start_time = time.time()  # Start the timer
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

        # Perform inference
        logger.info("Starting audio inference...")
        final_wave, final_sample_rate, _ = infer(
            ref_audio_path, ref_text, gen_text, remove_silence, cross_fade_duration, speed
        )

        # Output path for the generated audio
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        generated_audio_path = os.path.join(output_dir, "generated_audio.wav")
        sf.write(generated_audio_path, final_wave, final_sample_rate)

        execution_time = time.time() - start_time  # Calculate total time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")

        return FileResponse(
            path=generated_audio_path,
            filename="generated_audio.wav",
            media_type="audio/wav"
        )

    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating audio: {e}")


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
