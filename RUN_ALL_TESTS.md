# Complete Testing and Optimization Guide

## Overview

This guide covers three main tasks:
1. **Large Dataset Testing** - Validate generalization on multiple datasets
2. **Inference Speed Optimization** - Improve performance with GPU, batching, quantization
3. **Ensemble Integration** - Test CLIP + ResNet50 ensemble performance

---

## Step 1: Large Dataset Testing

### Purpose
Test ResNet50 on larger, diverse datasets to confirm it generalizes well beyond the initial 100-sample test.

### Run on Server

```bash
# Pull latest changes
git pull origin master

# Copy script to container
docker cp test_large_datasets.py secureai-backend:/app/

# Run large dataset testing
docker exec secureai-backend python /app/test_large_datasets.py
```

### What It Does
- Finds available test datasets (unified_deepfake, celeb_df_pp, etc.)
- Tests ResNet50 on each dataset
- Calculates accuracy, precision, recall, F1, AUC-ROC
- Generates report: `large_dataset_test_results.json`

### Expected Results
- **Good**: Accuracy >85% across multiple datasets
- **Excellent**: Accuracy >90% with consistent performance
- **Concern**: Accuracy varies significantly between datasets (overfitting)

---

## Step 2: Inference Speed Optimization

### Purpose
Optimize inference speed using GPU, batch processing, quantization, and TorchScript.

### Run on Server

```bash
# Copy script to container
docker cp optimize_inference_speed.py secureai-backend:/app/

# Run optimization tests
docker exec secureai-backend python /app/optimize_inference_speed.py
```

### What It Tests
1. **Baseline Performance**: Current single-image inference speed
2. **Batch Processing**: Tests batch sizes 1, 4, 8, 16, 32
3. **Quantization**: Dynamic INT8 quantization (CPU only)
4. **TorchScript**: JIT compilation for faster inference

### Expected Improvements
- **Batch Processing**: 2-5x speedup (process multiple images together)
- **Quantization**: 2-4x speedup on CPU, smaller model size
- **TorchScript**: 10-30% speedup
- **GPU**: 10-50x speedup vs CPU (if GPU available)

### Output
- Report: `inference_optimization_report.json`
- Recommendations for best optimization strategy

---

## Step 3: Ensemble Integration Testing

### Purpose
Test the new CLIP + ResNet50 ensemble and compare against individual models.

### What Was Integrated
- **New File**: `ai_model/ensemble_detector.py`
  - Combines CLIP + ResNet50 + LAA-Net (when available)
  - Adaptive weighting based on model confidence
  - Better accuracy than individual models

- **Updated**: `ai_model/detect.py`
  - Added `model_type='ensemble'` option
  - Uses full ensemble (CLIP + ResNet50 + LAA-Net)

### Test Ensemble

```bash
# Test ensemble on a video
docker exec secureai-backend python -c "
from ai_model.detect import detect_fake
result = detect_fake('uploads/test_video.mp4', model_type='ensemble')
print(result)
"
```

### Compare Models

```bash
# Copy comparison script
docker cp test_ensemble_performance.py secureai-backend:/app/

# Run comparison (requires test videos)
docker exec secureai-backend python /app/test_ensemble_performance.py
```

### Expected Results
- **Ensemble** should outperform individual models
- **Accuracy**: Ensemble > ResNet > CLIP (typically)
- **Confidence**: Ensemble provides higher confidence scores

---

## Quick Start: Run All Tests

### On Your Server

```bash
# 1. Pull latest code
cd ~/secureai-deepfake-detection
git pull origin master

# 2. Copy all scripts to container
docker cp test_large_datasets.py secureai-backend:/app/
docker cp optimize_inference_speed.py secureai-backend:/app/
docker cp test_ensemble_performance.py secureai-backend:/app/

# 3. Run tests in sequence
echo "=== Large Dataset Testing ==="
docker exec secureai-backend python /app/test_large_datasets.py

echo "=== Inference Optimization ==="
docker exec secureai-backend python /app/optimize_inference_speed.py

echo "=== Ensemble Testing ==="
docker exec secureai-backend python /app/test_ensemble_performance.py
```

---

## Understanding Results

### Large Dataset Test Results

**Good Generalization:**
- Accuracy >85% across all datasets
- Consistent performance (low variance)
- Low false positive/negative rates

**Overfitting Indicators:**
- High accuracy on one dataset, low on others
- Significant variance between datasets
- **Action**: Need more diverse training data

### Optimization Results

**Best Strategy:**
- **GPU Available**: Use GPU with batch processing (10-50x speedup)
- **CPU Only**: Use quantization + batch processing (2-5x speedup)
- **Production**: Use TorchScript for consistent performance

### Ensemble Results

**Expected Improvements:**
- Ensemble accuracy > individual model accuracy
- Higher confidence on correct predictions
- Lower false positive rate

---

## Next Steps After Testing

1. **If Generalization is Good** (accuracy >85% across datasets):
   - ✅ Model is production-ready
   - Consider fine-tuning on specific use cases

2. **If Optimization Shows Significant Speedup**:
   - Implement batch processing in production API
   - Use GPU if available
   - Apply quantization for CPU deployments

3. **If Ensemble Outperforms Individual Models**:
   - Update API to use `model_type='ensemble'` by default
   - Monitor ensemble performance in production
   - Consider adding more models to ensemble

---

## Troubleshooting

### "No test datasets found"
- Download test datasets to `datasets/` directory
- Or use existing `datasets/train/` and `datasets/val/`

### "CUDA out of memory"
- Reduce batch size in optimization script
- Use CPU instead: Set `CUDA_VISIBLE_DEVICES=""`

### "Model file not found"
- Ensure ResNet50 model is in `ai_model/resnet_resnet50_final.pth`
- Check file permissions

### "Import errors"
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python path includes `ai_model/` directory

---

## Files Created

1. **test_large_datasets.py** - Large dataset generalization testing
2. **optimize_inference_speed.py** - Inference speed optimization
3. **ai_model/ensemble_detector.py** - CLIP + ResNet50 ensemble
4. **test_ensemble_performance.py** - Ensemble vs individual comparison

All scripts generate JSON reports with detailed metrics.

