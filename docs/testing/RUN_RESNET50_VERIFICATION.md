# ResNet50 Verification and Benchmarking Guide

## Quick Start

Run the comprehensive verification script to test ResNet50 model:

### On Your Local Machine

```bash
# Make sure you're in the project root
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"

# Run verification
python verify_resnet50_benchmark.py
```

### On Your Server (Docker Container)

```bash
# Copy script to container
docker cp verify_resnet50_benchmark.py secureai-backend:/app/

# Run verification inside container
docker exec secureai-backend python /app/verify_resnet50_benchmark.py
```

## What the Verification Checks

### Step 1: Model File Verification
- ✅ Checks if model file exists (`resnet_resnet50_final.pth` or `resnet_resnet50_best.pth`)
- ✅ Verifies file size and structure
- ✅ Checks if model has classifier head (indicates training)
- ✅ Counts model parameters

### Step 2: Model Loading
- ✅ Loads model into memory
- ✅ Verifies model can be initialized
- ✅ Checks device (CPU/GPU)

### Step 3: Inference Testing
- ✅ Tests inference on dummy data
- ✅ Measures inference speed
- ✅ Calculates throughput (FPS)

### Step 4: Benchmarking
- ✅ Tests on real images from test datasets
- ✅ Tests on fake images from test datasets
- ✅ Calculates accuracy metrics:
  - **Accuracy**: Overall correctness
  - **Precision**: How many "fake" predictions were actually fake
  - **Recall**: How many actual fakes were detected
  - **F1-Score**: Balanced metric
  - **AUC-ROC**: Area under ROC curve (detection quality)
- ✅ Generates confusion matrix
- ✅ Measures performance (inference time, throughput)

## Expected Results

### Good Performance Indicators

| Metric | Target | Good | Excellent |
|--------|--------|------|-----------|
| **Accuracy** | ≥90% | 85-90% | >90% |
| **Precision** | ≥85% | 80-85% | >85% |
| **Recall** | ≥85% | 80-85% | >85% |
| **F1-Score** | ≥85% | 80-85% | >85% |
| **AUC-ROC** | ≥0.90 | 0.85-0.90 | >0.90 |
| **Inference Time** | <50ms | 50-100ms | <50ms |
| **Throughput** | >20 FPS | 10-20 FPS | >20 FPS |

### Model Training Status

- **✅ Trained for Deepfake Detection**: 
  - Has classifier head with 2 classes (real/fake)
  - Expected accuracy: 85-95%
  
- **⚠️ ImageNet Pretrained Only**:
  - May not have deepfake-specific training
  - Expected accuracy: 70-80%
  - **Action needed**: Retrain on deepfake datasets

## Output Files

The script generates:
- `resnet50_verification_report.json` - Complete verification report with all metrics

## Interpreting Results

### If Accuracy is Low (<80%)
1. **Check if model is trained**: Look for "is_trained: true" in report
2. **If not trained**: Model needs training on deepfake datasets
3. **If trained but low accuracy**: May need:
   - More training data
   - Better data quality
   - Hyperparameter tuning

### If Inference is Slow (>100ms)
1. **Check device**: GPU should be faster than CPU
2. **Check batch size**: Processing single images is slower
3. **Consider optimization**: Model quantization, TensorRT, etc.

### If Test Data Not Found
The script will skip benchmarking if no test data is found. Expected locations:
- `datasets/train/real/` and `datasets/train/fake/`
- `datasets/val/real/` and `datasets/val/fake/`
- `datasets/unified_deepfake/train/` and `datasets/unified_deepfake/val/`

## Next Steps Based on Results

### If Model is Not Trained
1. Prepare training data in `datasets/train/real/` and `datasets/train/fake/`
2. Run training script:
   ```bash
   python train_resnet.py --epochs 50 --batch_size 32
   ```
3. Re-run verification after training

### If Accuracy is Below Target
1. **Collect more training data**: Use benchmark datasets (Celeb-DF++, FaceForensics++)
2. **Data augmentation**: Increase variety in training set
3. **Fine-tuning**: Continue training from current weights
4. **Ensemble**: Combine with CLIP for better accuracy

### If Everything Passes
✅ Model is ready for production use!
- Consider adding LAA-Net for additional 5-10% improvement
- Monitor performance on real-world data
- Set up continuous evaluation pipeline

## Troubleshooting

### "Model file not found"
- Check if model file exists in `ai_model/` directory
- Verify file name matches expected patterns
- Check file permissions

### "CUDA out of memory"
- Reduce batch size
- Use CPU instead: Set `CUDA_VISIBLE_DEVICES=""` before running

### "No test data found"
- Download test datasets
- Or create test set with known real/fake samples
- Place in expected directory structure

### "Import errors"
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python path includes `ai_model/` directory

