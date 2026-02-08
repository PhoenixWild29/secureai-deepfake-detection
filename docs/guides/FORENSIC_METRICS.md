# Forensic metrics

This document describes the forensic metrics returned with each scan and how to interpret them.

## Metrics overview

| Metric | Description | Notes |
|--------|-------------|------|
| **Spatial artifacts** | Neural patterns in high-frequency pixel domains | From frame analysis. |
| **Temporal consistency** | Optical flow / frame-to-frame consistency | Uses per-frame probabilities when available. |
| **Spectral density** | Color entropy and sensor noise | From frame analysis. |
| **Vocal / Audio** | Vocal authenticity score | **Audio pipeline when present;** otherwise video-only. See below. |

## Vocal / audio metric (audio pipeline)

When the video has an audio track and **ffmpeg** is available, the backend runs a real **audio pipeline**:

1. **Extract audio** from the video (ffmpeg to mono 16 kHz WAV).
2. **Analyze** the audio for:
   - **Duration sync:** Audio duration vs video duration (mismatch can indicate tampering or synthetic replacement).
   - **Energy stability:** Frame-wise RMS variance; natural speech has variation; very flat or erratic profiles can indicate synthetic or manipulated audio.
   - **Zero-crossing rate:** Typical range for speech; out-of-range values can indicate non-speech or synthetic voice.
3. **Score:** An **audio consistency score** (0-1) is computed and fused with the video-based fake probability to produce **vocal_authenticity** (65% audio, 35% video). The response includes **`audio_analyzed: true`** and the UI shows **"Vocal / Audio (analyzed)"**.

When there is **no audio track**, extraction **fails** (e.g. no ffmpeg), or the pipeline errors, the backend falls back to **video-only**: **vocal_authenticity** is derived only from the video fake probability, and **`audio_analyzed: false`**. The UI then shows **"Vocal / Audio (video-only)"**.

### Dependencies

- **ffmpeg:** From **imageio-ffmpeg** (already in requirements) or system. Used only for audio extraction.
- **scipy:** Used to read the extracted WAV (already in requirements). No extra Python packages are required.
