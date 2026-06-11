# Model Improvement Plan — Toward Best-in-Class Deepfake Detection

**Date:** 2026-05-30
**Goal:** Move from the current honest baseline to a genuinely competitive, sellable detector — and define "best in the world" in the way the field actually measures it.

---

## 1. What "best in the world" actually means here

In-domain accuracy on one dataset is **not** how serious deepfake detection is judged — a model can hit 0.95 AUC on Celeb-DF and collapse to 0.6 on deepfakes it hasn't seen. The metric that matters for a product is **cross-dataset (cross-manipulation) generalization**: train on one source, test on *unseen* generators.

So our target benchmark, from day one, is a **cross-dataset AUC table**, not a single number:

| Train set | Test set (unseen) | What it proves |
|-----------|-------------------|----------------|
| FaceForensics++ (c23) | Celeb-DF v2 | classic generalization benchmark |
| FF++ | DFDC (preview/full) | robustness to in-the-wild quality |
| FF++ | DeepFakeDetection (DFD) | unseen actors/methods |
| FF++ + diffusion data | WildDeepfake | real-world social-media fakes |
| FF++ + diffusion data | a held-out diffusion/GAN set | coverage of fully-synthetic faces (2025+ threat) |

**Current SOTA reference points** (published cross-dataset, FF++→Celeb-DF): strong methods are in the **~0.90–0.93 AUC** range; the very best generalization papers push higher. "Best in the world" = matching or beating that cross-dataset number *and* covering modern diffusion-generated faces, which most older detectors miss.

> Reality check: our current honest baseline (ResNet50 AUC 0.906 / learned ensemble 0.936) is **in-domain on Celeb-DF v2** — i.e. trained and tested on the same dataset family. The cross-dataset number is almost certainly much lower today and is the gap we need to close.

---

## 2. Honest current baseline (post-cleanup)

| Model | Dataset | AUC | Notes |
|-------|---------|-----|-------|
| ResNet50 (Kaggle) | Celeb-DF v2 (in-domain) | 0.906 | clean training, the real workhorse |
| ConvNeXt-Base | Celeb-DF v2 (in-domain) | 0.915 | self-reports mild overfit |
| FFT logistic | Celeb-DF v2 | — | frequency artifacts; small positive contribution |
| **Learned ensemble** | Celeb-DF v2 (val) | **0.964** | recomputed; resnet50+convnext carry it |
| CLIP zero-shot | Celeb-DF v2 | 0.499 | chance — down-weighted to ~0 |
| LAA-Net (as wired) | Celeb-DF v2 | 0.494 | chance — fed full frames, not aligned faces |
| SBI ResNet50 | — | 0.608 | misconfigured run; SBI done right is SOTA-grade |

Two of these (CLIP, LAA) are *capable* methods that scored at chance only because of how they were plugged in — see P0 below.

---

## 3. Prioritized experiment roadmap

Ordered by **expected gain per unit effort**. P0 items are the highest-leverage and should happen first.

### P0 — Foundations (do these before any new architecture)

**P0.1 — Aligned face-crop pipeline (the single biggest lever).**
Every strong detector operates on detected, aligned **face crops**, not full frames. Train *and* infer on MTCNN/RetinaFace crops (margin ~30%, aligned by landmarks, resized to the backbone's input). This typically adds several AUC points, fixes LAA-Net immediately, and is essential for cross-dataset transfer. *(Inference side is already wired in code via `EnhancedDetector.crop_faces`; the training data must be re-extracted as face crops to match.)*
Expected gain: large. Effort: medium (re-extract frames as faces, retrain).

**P0.2 — Cross-dataset evaluation harness.**
Build a fixed eval script that reports AUC + AP + EER + accuracy@FPR=0.1 for every (train, test) pair in the table above, with **identity-disjoint** splits. Without this you can't tell real progress from overfitting. This is also your sales/credibility artifact.
Effort: low–medium. Gain: enables everything else.

**P0.3 — Add FaceForensics++ and DFDC to training.**
Celeb-DF-only training will never generalize. FF++ (c23/c40 compression levels) is the standard training source; DFDC adds real-world variability. Train on FF++, validate on Celeb-DF as the canonical generalization check.
Effort: medium (data acquisition + extraction). Gain: large for cross-dataset.

### P1 — Generalization techniques (where SOTA actually comes from)

**P1.1 — Fix and adopt Self-Blended Images (SBI).**
SBI/blending-based augmentation synthesizes "fakes" from real faces and is one of the strongest *generalization* recipes in the literature. The existing SBI run scored 0.61 — that's a misconfiguration, not a verdict on the method. Re-implement carefully (source-target blending, correct masks, consistency loss) on aligned faces.
Effort: medium–high. Gain: potentially the biggest cross-dataset jump.

**P1.2 — Compression / robustness augmentation.**
Train with random JPEG quality, H.264 re-encoding, downscale-upscale, blur, and noise so the model survives social-media re-compression. DFDC-winning solutions leaned heavily on this.
Effort: low. Gain: medium (robustness, fewer false negatives on real uploads).

**P1.3 — Properly integrate LAA-Net (or drop it).**
On aligned faces with its native preprocessing, LAA-Net is a strong localized-artifact detector. Either fix the preprocessing so it earns real ensemble weight, or remove it from the product story. Don't ship it scoring 0.49.
Effort: medium. Gain: medium.

**P1.4 — Frequency + spatial fusion.**
Keep the FFT/DCT branch but fuse it properly (two-stream or feature-level), since GAN/diffusion artifacts often show up in frequency space.
Effort: medium. Gain: small–medium, complementary.

### P2 — Modern coverage & polish

**P2.1 — Diffusion/GAN fully-synthetic face coverage.**
2025+ threats include faces with no "real source" (Midjourney/SD/StyleGAN portraits). Add a diffusion-generated face dataset (e.g. DiFF-style) so the product detects synthetic faces, not just face-swaps. This is required to credibly claim modern coverage — and lets you *honestly* re-add the "diffusion-aware" capability the README used to overclaim.
Effort: medium. Gain: closes a real product gap.

**P2.2 — Video-level temporal aggregation.**
Move beyond frame-mean: model temporal inconsistency (per-frame scores → temporal smoothing / small sequence model), which catches flicker artifacts and stabilizes the verdict.
Effort: medium. Gain: small–medium, improves UX confidence.

**P2.3 — Confidence calibration.**
Apply temperature scaling or isotonic regression on a held-out set so the "confidence %" shown to users is meaningful (a calibrated 0.8 should be right ~80% of the time). Critical for a product people trust and pay for.
Effort: low. Gain: trust/UX (not AUC, but matters commercially).

**P2.4 — Test-time augmentation.**
Average over horizontal flip + multi-crop at inference for a small, free AUC bump.
Effort: low. Gain: small.

---

## 4. Concrete next training runs (for your GPU env — Kaggle/Colab)

You already have `kaggle_training_code.py`, `convnext_colab_training.ipynb`, and `sbi_training.ipynb`. The upgrades needed, in order:

1. **Re-extract training frames as aligned face crops** (new preprocessing step) — feeds every run below.
2. **Run A — Generalization baseline:** EfficientNet-B4 or ConvNeXt-Base on **FF++ c23 face crops** + compression aug; evaluate cross-dataset on Celeb-DF/DFDC via the new harness. This becomes your honest headline number.
3. **Run B — SBI done right:** same backbone, SBI augmentation on aligned faces; compare cross-dataset AUC to Run A.
4. **Run C — Ensemble refit:** refit the logistic ensemble over the *new* detectors' cross-dataset val scores (reuse the existing `ensemble_weights.json` mechanism — it works well).
5. **Run D — Diffusion coverage:** fold a diffusion/GAN face set into training; verify it doesn't regress face-swap performance.

I can implement the upgraded training code (face-crop extraction, compression/SBI augmentation, the cross-dataset eval harness, and the ensemble refit script) so you just run the cells on GPU — say the word and I'll build them.

---

## 5. Evaluation discipline (non-negotiable for a sellable product)

- **Identity-disjoint splits** always — no subject's frames in both train and test (this is exactly the leakage that produced the fake "100%" model we removed).
- Report **cross-dataset** AUC/AP/EER, not just in-domain.
- Per-manipulation and per-compression breakdowns so you know failure modes.
- A **frozen held-out test set** never touched during development.
- Re-run `tests/test_detection_correctness.py` (and extend it) so detection can't silently regress again.

---

## 6. Honest positioning while you improve

Until the cross-dataset numbers are in, market the product on what's true: a calibrated ensemble at **~0.93–0.96 AUC in-domain on Celeb-DF v2**, with active work on cross-dataset generalization and diffusion coverage. That's a credible, defensible story — and far stronger than a fabricated 94.2% that a technical buyer would dismantle in five minutes.
