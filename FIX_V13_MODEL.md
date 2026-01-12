# Fix V13 Model Loading

## Problem
The V13 model path `ash12321/deepfake-detector-v13` may not exist on Hugging Face, or the model structure is different than expected.

## Solution
Updated the loading code to:
1. Try multiple possible model names
2. Try multiple loading approaches (AutoModel, ViTForImageClassification, ConvNextForImageClassification)
3. Gracefully fall back if model doesn't exist

## Test V13 Model

Run this to find the correct model:

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy test script
docker cp find_v13_model.py secureai-backend:/app/

# Run search
docker exec secureai-backend python3 find_v13_model.py
```

This will:
- Test multiple possible model names
- Try different loading approaches
- Show which model works (if any)
- List alternative models on Hugging Face

## After Finding Model

Once we know the correct model name, we'll update the code to use it.

## Alternative: Use V12

If V13 doesn't exist, we can use V12 which has similar performance:
- V12: 97.94% accuracy, F1: 0.9715
- V13: 95.86% F1 (claimed)

V12 might actually be better!

## Next Steps

1. Run the search script to find the correct model
2. Update code with correct model name
3. Test loading
4. Integrate into ensemble
