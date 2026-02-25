"""
Audio pipeline for deepfake forensic metrics.
Extracts audio from video, runs basic consistency and authenticity checks,
and produces a vocal/audio authenticity score for use in forensic_metrics.
"""
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Frame size for short-term features (e.g. 25 ms at 16 kHz = 400 samples)
FRAME_LEN_SAMPLES = 400
# Hop length
HOP_LEN_SAMPLES = 200


def _get_ffmpeg_exe() -> Optional[str]:
    """Return path to ffmpeg binary (imageio-ffmpeg or system)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for name in ("ffmpeg", "avconv"):
        try:
            subprocess.run([name, "-version"], capture_output=True, check=True, timeout=5)
            return name
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return None


def extract_audio(
    video_path: str,
    sample_rate: int = 16000,
    max_duration_sec: float = 300.0,
) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Extract audio from video to a temporary WAV file (mono, 16 kHz).
    Returns (wav_path, duration_sec, error_message). duration_sec is 0 if extraction failed.
    """
    ffmpeg = _get_ffmpeg_exe()
    if not ffmpeg:
        return None, 0.0, "ffmpeg not available"
    if not os.path.isfile(video_path):
        return None, 0.0, "video file not found"
    try:
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        cmd = [
            ffmpeg,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            "-t", str(max_duration_sec),
            "-loglevel", "error",
            wav_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0 or not os.path.isfile(wav_path):
            if os.path.isfile(wav_path):
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
            return None, 0.0, result.stderr or "ffmpeg failed"
        try:
            import scipy.io.wavfile as wavfile
            sr, data = wavfile.read(wav_path)
            if data.size == 0:
                os.unlink(wav_path)
                return None, 0.0, "empty audio"
            duration_sec = len(data) / float(sr)
            return wav_path, duration_sec, None
        except Exception as e:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
            return None, 0.0, str(e)
    except subprocess.TimeoutExpired:
        return None, 0.0, "ffmpeg timeout"
    except Exception as e:
        return None, 0.0, str(e)


def _rms(signal: np.ndarray) -> float:
    """RMS energy of a segment."""
    if signal.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(signal.astype(np.float64) ** 2)))


def _zcr(signal: np.ndarray) -> float:
    """Zero-crossing rate."""
    if signal.size < 2:
        return 0.0
    s = signal.astype(np.float64)
    return float(np.mean(np.abs(np.diff(np.sign(s)))) / 2.0)


def analyze_audio(
    wav_path: str,
    video_duration_sec: float,
    sample_rate: int = 16000,
) -> Dict[str, Any]:
    """
    Analyze extracted audio for consistency and authenticity indicators.
    Returns dict with has_audio=True, duration_ok, features, and audio_consistency_score (0-1).
    """
    out: Dict[str, Any] = {
        "has_audio": True,
        "duration_ok": False,
        "audio_duration_sec": 0.0,
        "video_duration_sec": video_duration_sec,
        "rms_variance": 0.0,
        "zcr_mean": 0.0,
        "energy_stability": 0.0,
        "audio_consistency_score": 0.5,
    }
    try:
        import scipy.io.wavfile as wavfile
        sr, data = wavfile.read(wav_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        data = data.astype(np.float64) / (2 ** 15)
        duration_sec = len(data) / float(sr)
        out["audio_duration_sec"] = duration_sec
        # Duration match (allow 10% tolerance or 2 sec)
        if video_duration_sec > 0:
            diff = abs(duration_sec - video_duration_sec)
            out["duration_ok"] = diff <= max(2.0, video_duration_sec * 0.1)
        else:
            out["duration_ok"] = duration_sec > 0.5
        # Frame-based features
        n_frames = max(1, (len(data) - FRAME_LEN_SAMPLES) // HOP_LEN_SAMPLES)
        rms_list = []
        zcr_list = []
        for i in range(n_frames):
            start = i * HOP_LEN_SAMPLES
            end = start + FRAME_LEN_SAMPLES
            if end > len(data):
                break
            frame = data[start:end]
            rms_list.append(_rms(frame))
            zcr_list.append(_zcr(frame))
        if not rms_list:
            out["audio_consistency_score"] = 0.5
            return out
        rms_arr = np.array(rms_list)
        zcr_arr = np.array(zcr_list)
        out["rms_variance"] = float(np.var(rms_arr))
        out["zcr_mean"] = float(np.mean(zcr_arr))
        # Energy stability: natural speech has variation; very low or very high variance can be suspicious
        # Normalize variance to a 0-1 "natural" score (heuristic)
        rms_std = np.std(rms_arr)
        # Too flat (synthetic/robotic) or too erratic (noise/tampering) -> lower score
        if rms_std < 1e-6:
            energy_stability = 0.2
        else:
            # Typical speech RMS std in normalized signal is in a range; map to 0-1
            energy_stability = float(np.clip(0.5 + (rms_std - 0.02) * 10, 0.0, 1.0))
        out["energy_stability"] = energy_stability
        # Combine: duration match + energy stability + ZCR in typical speech range (0.05-0.5)
        zcr_ok = 0.05 <= out["zcr_mean"] <= 0.5
        duration_score = 1.0 if out["duration_ok"] else 0.4
        consistency = 0.4 * duration_score + 0.4 * energy_stability + (0.2 if zcr_ok else 0.0)
        out["audio_consistency_score"] = float(np.clip(consistency, 0.0, 1.0))
        return out
    except Exception as e:
        logger.warning(f"Audio analysis failed: {e}")
        out["has_audio"] = True
        out["audio_consistency_score"] = 0.5
        return out


def run_audio_pipeline(
    video_path: str,
    video_duration_sec: float,
) -> Dict[str, Any]:
    """
    Full pipeline: extract audio from video, analyze it, return result for forensic metrics.
    Returns dict with has_audio (bool), audio_analyzed (bool), vocal_authenticity (float),
    and optional details (duration_ok, audio_consistency_score, etc.).
    """
    result: Dict[str, Any] = {
        "has_audio": False,
        "audio_analyzed": False,
        "vocal_authenticity": 0.5,
        "details": None,
    }
    wav_path, audio_duration, err = extract_audio(video_path)
    if err or not wav_path:
        logger.info(f"Audio pipeline: skipped or failed (reason: {err or 'no wav path'})")
        return result
    try:
        analysis = analyze_audio(wav_path, video_duration_sec)
        result["has_audio"] = True
        result["audio_analyzed"] = True
        result["vocal_authenticity"] = analysis["audio_consistency_score"]
        result["details"] = {
            "duration_ok": analysis["duration_ok"],
            "audio_consistency_score": analysis["audio_consistency_score"],
            "audio_duration_sec": analysis["audio_duration_sec"],
        }
        logger.info(f"Audio pipeline: analyzed OK, duration_sec={analysis['audio_duration_sec']:.1f}, consistency={analysis['audio_consistency_score']:.3f}")
        return result
    finally:
        try:
            if wav_path and os.path.isfile(wav_path):
                os.unlink(wav_path)
        except OSError:
            pass
