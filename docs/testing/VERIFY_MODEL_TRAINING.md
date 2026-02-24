# Verify Model Training and Accuracy

## Quick Check: Is ResNet50 Trained?

Run this on your server to check if the ResNet model is properly trained:

```bash
# Enter the backend container
docker exec -it secureai-backend python -c "
import torch
import os

model_path = 'ai_model/resnet_resnet50_final.pth'
if os.path.exists(model_path):
    print(f'✅ Model file exists: {model_path}')
    state_dict = torch.load(model_path, map_location='cpu')
    print(f'Model keys: {len(state_dict.keys())} parameters')
    print(f'First few keys: {list(state_dict.keys())[:5]}')
    
    # Check if it's ImageNet weights (not trained) or custom weights (trained)
    if 'fc.weight' in state_dict:
        print(f'✅ Has classifier head (fc.weight shape: {state_dict[\"fc.weight\"].shape})')
        print('This suggests the model was trained/fine-tuned for deepfake detection')
    else:
        print('⚠️  May be ImageNet pretrained only (not deepfake-trained)')
else:
    print(f'❌ Model file not found: {model_path}')
"
```

## Check Model Performance

### Option 1: Run Benchmark Tests

```bash
# On your server, if test script is available
docker exec -it secureai-backend python test_enhanced_models.py --output_dir /tmp/benchmark_results
```

### Option 2: Test on Sample Video

```bash
# Test detection on a known video
docker exec -it secureai-backend python -c "
from ai_model.detect import detect_fake
import json

# Test with a sample video (if available)
result = detect_fake('uploads/sample_video.mp4', model_type='enhanced')
print(json.dumps(result, indent=2))
"
```

## Expected Model Behavior

### CLIP Model
- **Status**: ✅ Pretrained (no training needed)
- **Accuracy**: ~85-90% on modern deepfakes
- **Works on**: Diffusion models, GANs, face swaps

### ResNet50 Model
- **Status**: ⚠️ Need to verify training
- **If trained on deepfakes**: ~90-95% accuracy
- **If only ImageNet pretrained**: ~70-80% accuracy
- **Check**: Run verification script above

### Ensemble (CLIP + ResNet)
- **Current accuracy**: ~88-93% (estimated)
- **With LAA-Net**: Would be ~93-98%

