import tempfile
import soundfile as sf
import torchaudio
import numpy as np
from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_vocoder,
    load_model,
    infer_process,
    remove_silence_for_generated_wav,
    save_spectrogram,
)
from cached_path import cached_path
from config import gpu_decorator, logger
from utils.text import translate_number_to_text

# Load TTS models
vocoder = load_vocoder()
F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
F5TTS_ema_model = load_model(
    DiT, 
    F5TTS_model_cfg, 
    str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
)

@gpu_decorator
def infer(ref_audio_orig, ref_text, gen_text, remove_silence=False, 
          cross_fade_duration=0.15, speed=1.0, nfe_step=8):
    """Generate audio using F5-TTS model"""
    logger.info("Starting text preprocessing...")
    gen_text = gen_text.lower()
    gen_text = translate_number_to_text(gen_text)
    
    # Inference process
    final_wave, final_sample_rate, combined_spectrogram = infer_process(
        ref_audio_orig, ref_text, gen_text, F5TTS_ema_model, vocoder,
        cross_fade_duration=cross_fade_duration, speed=speed, nfe_step=nfe_step
    )
    
    # Remove silence if requested
    if remove_silence:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wave:
            sf.write(tmp_wave.name, final_wave, final_sample_rate)
            remove_silence_for_generated_wav(tmp_wave.name)
            final_wave, _ = torchaudio.load(tmp_wave.name)
        final_wave = final_wave.squeeze().cpu().numpy()
    
    # Save spectrogram
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_spectrogram:
        spectrogram_path = tmp_spectrogram.name
        save_spectrogram(combined_spectrogram, spectrogram_path)
    
    logger.info("Inference completed successfully.")
    return final_wave, final_sample_rate, spectrogram_path