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

---

## How to verify the audio pipeline is working

Use any of these to confirm whether audio was actually analyzed for a scan.

### 1. UI (Guardian results)

After a scan, open the **Multi-Layer Metric Deep-Dive** section:

- **"Vocal / Audio (analyzed)"** with description *"Audio extracted and analyzed: duration sync, energy stability, voice consistency."* → **Audio pipeline ran.** The vocal metric used real audio.
- **"Vocal / Audio (video-only)"** with *"Video-only (no audio track or extraction failed)."* → **Audio was not analyzed.** Either the file had no audio, or extraction failed (e.g. ffmpeg missing in the environment).

### 2. API response

In the scan result JSON, check **`forensic_metrics`**:

- **`audio_analyzed: true`** and **`audio_pipeline_status: "analyzed"`** → Audio was extracted and analyzed.
- **`audio_analyzed: false`** and **`audio_pipeline_status: "video_only"`** → Video-only path was used.

You can inspect this in the browser **Developer Tools → Network** tab: select the request that returns the analysis, then look at the response body for `forensic_metrics`.

### 3. Server logs

On the server (e.g. where the backend runs), after a scan:

- **Audio analyzed:** You should see a line like:  
  `Forensic metrics: audio analyzed, vocal_authenticity=0.XXX (audio_consistency=0.XXX)`  
  and:  
  `Audio pipeline: analyzed OK, duration_sec=X.X, consistency=0.XXX`
- **Audio skipped/failed:** You should see one of:  
  `Audio pipeline: skipped or failed (reason: ffmpeg not available)`  
  `Audio pipeline: skipped or failed (reason: ...)`  
  `Forensic metrics: audio pipeline did not run (no audio track or extraction failed), using video-only vocal score`  
  or:  
  `Forensic metrics: audio pipeline error (...), using video-only vocal score`

Example (view backend logs on the server):

```bash
docker compose -f docker-compose.https.yml logs -f secureai-backend
```

Run a scan, then check the log lines above. If you always see "skipped or failed" or "did not run", the most common cause is **ffmpeg not available** inside the backend container (e.g. imageio-ffmpeg not installed in the image, or the binary not on PATH). Ensure the Docker build installs Python deps so **imageio-ffmpeg** is present; it bundles the ffmpeg binary.
