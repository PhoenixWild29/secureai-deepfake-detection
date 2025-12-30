# 📖 Complete Usage Guide - SecureAI DeepFake Detection

This guide covers everything you need to know to use the deepfake detection system effectively.

## 🎯 Table of Contents

1. [Running the System](#running-the-system)
2. [Detection Methods](#detection-methods)
3. [Web Interface Guide](#web-interface-guide)
4. [Command Line Usage](#command-line-usage)
5. [Batch Processing](#batch-processing)
6. [Understanding Results](#understanding-results)
7. [Training Your Own Models](#training-your-own-models)
8. [API Integration](#api-integration)

---

## 🚀 Running the System

### Method 1: Interactive Quick Start (Easiest)

```bash
python quick_start.py
```

This interactive script will:
- Check your system requirements
- Verify installed dependencies
- Find test videos
- Let you choose what to do next

**Best for:** First-time users

### Method 2: Simple Demo (Quick Testing)

```bash
# Test a specific video
python simple_demo.py path/to/video.mp4

# Or run without arguments to select from available videos
python simple_demo.py
```

**Best for:** Quick tests, single videos, command-line users

### Method 3: Web Interface (Full Features)

```bash
python api.py
```

Then open: http://localhost:5000

**Best for:** Multiple videos, sharing with others, visualization, production use

---

## 🤖 Detection Methods

The system offers multiple AI models for different use cases:

### 1. ResNet Model (Default, Recommended)

```python
from ai_model.detect import detect_fake
result = detect_fake('video.mp4', model_type='resnet')
```

**Characteristics:**
- ✓ Most reliable and stable
- ✓ Good accuracy (90%+ on standard datasets)
- ✓ Works well with various video qualities
- ⚠ Moderate speed (10-30s per video)

**Best for:** General purpose, production use

### 2. Enhanced SOTA Model (Most Accurate)

```python
result = detect_fake('video.mp4', model_type='enhanced')
```

**Characteristics:**
- ✓ Highest accuracy (94%+ on benchmarks)
- ✓ Uses ensemble of LAA-Net, CLIP, and DM-aware techniques
- ✓ Handles difficult cases better
- ⚠ Slower processing (30-60s per video)
- ⚠ Requires more memory

**Best for:** Critical applications, difficult videos, best accuracy needed

### 3. CNN Classifier (Fast)

```python
result = detect_fake('video.mp4', model_type='cnn')
```

**Characteristics:**
- ✓ Fast processing (5-15s per video)
- ✓ Lower memory usage
- ⚠ Slightly lower accuracy (85-88%)

**Best for:** Quick scans, batch processing, resource-constrained environments

### 4. Ensemble (Adaptive)

```python
result = detect_fake('video.mp4', model_type='ensemble')
```

**Characteristics:**
- ✓ Tries enhanced first, falls back to CNN
- ✓ Good balance of accuracy and reliability
- ⚠ Variable processing time

**Best for:** Unknown video types, automated systems

---

## 🖥️ Web Interface Guide

### Starting the Web Server

```bash
python api.py
```

Access at: **http://localhost:5000**

### Main Features

#### 1. Video Upload & Analysis

**Steps:**
1. Click "Upload Video" or drag & drop
2. Select video file (.mp4, .avi, .mov, .mkv, .webm)
3. Click "Analyze"
4. Wait for results (progress bar shows status)
5. View detailed results

**What you see:**
- 🚨 FAKE or ✓ AUTHENTIC verdict
- Confidence percentage
- Processing time
- Video hash for verification
- Frame analysis details

#### 2. History & Analytics

**Access:** Click "History" tab

**Features:**
- View all past analyses
- Sort by date, result, confidence
- Export results as JSON
- Delete old analyses
- Search by filename

#### 3. Batch Upload

**Steps:**
1. Click "Batch Upload"
2. Select multiple videos
3. Click "Process Batch"
4. Monitor progress
5. Download batch report

**Limitations:**
- Max 50 videos per batch
- Max 500MB per video
- Processing time depends on total size

#### 4. Statistics Dashboard

**Access:** Click "Stats" tab

**Metrics shown:**
- Total videos analyzed
- Fake vs Authentic ratio
- Average processing time
- Detection accuracy trends
- Usage over time graphs

### API Endpoints (for Developers)

```bash
# Health check
GET /api/health

# Analyze single video
POST /api/analyze
Body: { "video": <file> }

# Batch analysis
POST /api/batch
Body: { "videos": [<files>] }

# Get analysis history
GET /api/history

# Get statistics
GET /api/stats

# Get specific result
GET /api/result/<analysis_id>
```

---

## 💻 Command Line Usage

### Basic Detection

```bash
# Using Python API
python -c "from ai_model.detect import detect_fake; print(detect_fake('video.mp4'))"

# Using simple demo
python simple_demo.py video.mp4
```

### Specify Model Type

```python
# In Python script
from ai_model.detect import detect_fake

# Try different models
result_resnet = detect_fake('video.mp4', model_type='resnet')
result_enhanced = detect_fake('video.mp4', model_type='enhanced')
result_cnn = detect_fake('video.mp4', model_type='cnn')

print(f"ResNet: {result_resnet['is_fake']}")
print(f"Enhanced: {result_enhanced['is_fake']}")
print(f"CNN: {result_cnn['is_fake']}")
```

### Benchmark All Models

```python
from ai_model.detect import benchmark_models

results = benchmark_models('video.mp4')
for model, result in results.items():
    if result['success']:
        print(f"{model}: {result['result']['is_fake']} ({result['processing_time']:.2f}s)")
```

---

## 📦 Batch Processing

### Using Batch Processor Script

```bash
# Process entire folder
python batch_processor.py --input_dir videos/ --output_dir results/

# With specific model
python batch_processor.py --input_dir videos/ --model_type enhanced

# Generate report
python batch_processor.py --input_dir videos/ --generate_report
```

### Programmatic Batch Processing

```python
import os
from ai_model.detect import detect_fake

video_folder = 'videos/'
results = []

for filename in os.listdir(video_folder):
    if filename.endswith(('.mp4', '.avi', '.mov')):
        video_path = os.path.join(video_folder, filename)
        result = detect_fake(video_path)
        results.append({
            'filename': filename,
            'is_fake': result['is_fake'],
            'confidence': result['confidence']
        })

# Save results
import json
with open('batch_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Processed {len(results)} videos")
```

### Batch Processing Best Practices

1. **Sort by size**: Process smaller videos first for quick wins
2. **Monitor memory**: Close other applications for large batches
3. **Save incrementally**: Save results after each video to avoid data loss
4. **Use appropriate model**: Use 'cnn' for speed, 'enhanced' for accuracy
5. **Parallel processing**: Consider using multiple workers for large batches

---

## 📊 Understanding Results

### Result Structure

```python
{
    'is_fake': True/False,           # Verdict
    'confidence': 0.0-1.0,           # Model confidence
    'authenticity_score': 0.0-1.0,   # For authentic videos
    'video_hash': 'sha256_hash',     # Unique video identifier
    'processing_time': 12.5,         # Seconds
    'method': 'resnet',              # Model used
    'frames_analyzed': 150,          # Number of frames
    'frame_details': [...],          # Per-frame analysis (optional)
    'error': 'message'               # If error occurred
}
```

### Interpreting Confidence Scores

| Confidence | Interpretation | Action |
|------------|---------------|--------|
| 90-100% | Very High | Trust the result |
| 80-90% | High | Likely accurate |
| 70-80% | Medium-High | Good confidence |
| 60-70% | Medium | Consider manual review |
| 50-60% | Low-Medium | Manual review recommended |
| 0-50% | Low | Video may be unclear |

### Common Result Scenarios

#### Scenario 1: High Confidence Fake
```python
{
    'is_fake': True,
    'confidence': 0.95,
    'authenticity_score': 0.05
}
```
**Interpretation:** Strong indicators of deepfake detected. Very likely manipulated.

#### Scenario 2: High Confidence Authentic
```python
{
    'is_fake': False,
    'confidence': 0.12,
    'authenticity_score': 0.88
}
```
**Interpretation:** No significant deepfake artifacts found. Likely authentic.

#### Scenario 3: Low Confidence
```python
{
    'is_fake': False,
    'confidence': 0.55,
    'authenticity_score': 0.45
}
```
**Interpretation:** Unclear result. Could be:
- Low quality video
- Unusual lighting/angles
- Borderline case
- Video compression artifacts

**Action:** Manual review recommended

### False Positives & False Negatives

**False Positive** (Authentic marked as Fake):
- Caused by: Heavy makeup, unusual lighting, video filters
- Solution: Try 'enhanced' model, check with multiple models

**False Negative** (Fake marked as Authentic):
- Caused by: High-quality deepfakes, subtle manipulations
- Solution: Look for secondary indicators, use ensemble model

---

## 🎓 Training Your Own Models

### Why Train Custom Models?

- Specialize for specific video types
- Improve accuracy on your dataset
- Adapt to new deepfake techniques
- Reduce false positives for your use case

### Quick Training

```bash
# Train ResNet model
python ai_model/train_enhanced.py --epochs 50 --batch_size 8

# Train with specific datasets
python ai_model/train_enhanced.py --dataset celeb_df --epochs 30

# Train enhanced SOTA model
python ai_model/train_enhanced.py --use_laa --use_clip --use_dm_aware
```

### Training Parameters

```bash
--epochs          # Number of training epochs (default: 50)
--batch_size      # Batch size (default: 8, reduce if OOM)
--learning_rate   # Learning rate (default: 0.001)
--dataset         # Dataset to use (default: unified_deepfake)
--model_type      # Model architecture (resnet, cnn, enhanced)
--use_laa         # Enable LAA-Net (advanced)
--use_clip        # Enable CLIP-based detection
--use_dm_aware    # Enable diffusion model awareness
```

### Using Your Trained Model

```python
from ai_model.deepfake_classifier import ResNetDeepfakeClassifier

# Load your custom model
model = ResNetDeepfakeClassifier(model_path='path/to/your/model.pth')
result = model.predict_video('video.mp4')
```

---

## 🔌 API Integration

### Python Integration

```python
from ai_model.detect import detect_fake

def check_video(video_path):
    result = detect_fake(video_path)
    
    if result['is_fake'] and result['confidence'] > 0.8:
        print("⚠️ WARNING: Deepfake detected!")
        return False
    else:
        print("✓ Video appears authentic")
        return True

# Use in your application
if check_video('uploaded_video.mp4'):
    # Process authentic video
    save_to_database()
else:
    # Flag for review
    mark_for_moderation()
```

### REST API Integration

```python
import requests

# Upload video for analysis
url = 'http://localhost:5000/api/analyze'
files = {'video': open('video.mp4', 'rb')}
response = requests.post(url, files=files)
result = response.json()

print(f"Is Fake: {result['result']['is_fake']}")
print(f"Confidence: {result['result']['confidence']}")
```

### JavaScript/Node.js Integration

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function analyzeVideo(videoPath) {
    const form = new FormData();
    form.append('video', fs.createReadStream(videoPath));
    
    const response = await axios.post(
        'http://localhost:5000/api/analyze',
        form,
        { headers: form.getHeaders() }
    );
    
    return response.data;
}

// Usage
analyzeVideo('video.mp4').then(result => {
    console.log('Is Fake:', result.result.is_fake);
    console.log('Confidence:', result.result.confidence);
});
```

---

## 🎯 Use Case Examples

### Use Case 1: Content Moderation Platform

```python
def moderate_upload(video_file):
    # Analyze video
    result = detect_fake(video_file)
    
    # Make decision based on confidence
    if result['is_fake'] and result['confidence'] > 0.85:
        return {
            'status': 'rejected',
            'reason': 'Deepfake detected with high confidence',
            'details': result
        }
    elif result['confidence'] > 0.60:
        return {
            'status': 'review',
            'reason': 'Requires manual review',
            'details': result
        }
    else:
        return {
            'status': 'approved',
            'details': result
        }
```

### Use Case 2: News Verification

```python
def verify_news_video(video_path, threshold=0.90):
    result = detect_fake(video_path, model_type='enhanced')
    
    verification_report = {
        'video_hash': result['video_hash'],
        'timestamp': datetime.now().isoformat(),
        'verdict': 'authentic' if not result['is_fake'] else 'manipulated',
        'confidence': result['confidence'],
        'verified': result['confidence'] > threshold
    }
    
    return verification_report
```

### Use Case 3: Batch Video Library Scan

```python
import os
from tqdm import tqdm

def scan_video_library(library_path):
    suspicious_videos = []
    
    videos = [f for f in os.listdir(library_path) 
              if f.endswith(('.mp4', '.avi'))]
    
    for video in tqdm(videos, desc="Scanning"):
        video_path = os.path.join(library_path, video)
        result = detect_fake(video_path, model_type='cnn')  # Fast model
        
        if result['is_fake'] and result['confidence'] > 0.75:
            suspicious_videos.append({
                'filename': video,
                'confidence': result['confidence']
            })
    
    return suspicious_videos
```

---

## 💡 Tips & Best Practices

### Performance Optimization

1. **Use GPU**: 5-10x faster processing
   ```bash
   # Check CUDA availability
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Reduce frame count**: Process fewer frames for speed
   ```python
   # Modify in deepfake_classifier.py
   max_frames = 30  # Instead of default 150
   ```

3. **Batch processing**: Process multiple videos efficiently
   ```bash
   python batch_processor.py --input_dir videos/ --workers 4
   ```

### Accuracy Improvements

1. **Use ensemble voting**: Combine multiple models
2. **Adjust thresholds**: Based on your false positive/negative tolerance
3. **Train on similar data**: Custom models for your specific use case
4. **Quality check**: Ensure input videos are good quality

### Production Deployment

1. **Use async processing**: Don't block web requests
2. **Add caching**: Cache results by video hash
3. **Monitor performance**: Track processing times and errors
4. **Scale horizontally**: Use multiple worker processes
5. **Add rate limiting**: Prevent abuse

---

## 📞 Troubleshooting

See GETTING_STARTED.md for common issues and solutions.

---

**Happy detecting! 🎬🔍**


