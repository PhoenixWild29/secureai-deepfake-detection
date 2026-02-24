# ⚡ Quick Reference Cheatsheet

## 🚀 Installation (One Command)

```bash
pip install -r requirements.txt
```

## 🎯 Quick Commands

### Start Web Interface
```bash
python api.py
```
→ Open http://localhost:5000

### Test Single Video
```bash
python simple_demo.py video.mp4
```

### Interactive Start
```bash
python quick_start.py
```

### Batch Process Folder
```bash
python batch_processor.py --input_dir videos/
```

## 💻 Python API

### Basic Detection
```python
from ai_model.detect import detect_fake

result = detect_fake('video.mp4')
print(f"Fake: {result['is_fake']}")
print(f"Confidence: {result['confidence']}")
```

### Choose Model
```python
# Fast
result = detect_fake('video.mp4', model_type='cnn')

# Balanced (default, recommended)
result = detect_fake('video.mp4', model_type='resnet')

# Most accurate
result = detect_fake('video.mp4', model_type='enhanced')

# Adaptive
result = detect_fake('video.mp4', model_type='ensemble')
```

### Batch Processing
```python
import os
from ai_model.detect import detect_fake

for video in os.listdir('videos/'):
    if video.endswith('.mp4'):
        result = detect_fake(f'videos/{video}')
        print(f"{video}: {'FAKE' if result['is_fake'] else 'REAL'}")
```

## 🌐 REST API

### Analyze Video
```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "video=@video.mp4"
```

### Get History
```bash
curl http://localhost:5000/api/history
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

## 📊 Result Interpretation

| Confidence | Meaning | Action |
|------------|---------|--------|
| 90-100% | Very High | Trust it |
| 80-90% | High | Good |
| 70-80% | Medium-High | OK |
| 60-70% | Medium | Review |
| 0-60% | Low | Manual check |

## 🔧 Common Fixes

### Module not found
```bash
pip install -r requirements.txt
```

### Port in use
Change port in `api.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Out of memory
Use smaller batch size or CNN model:
```python
result = detect_fake('video.mp4', model_type='cnn')
```

### Slow processing
- Use GPU (10x faster)
- Use CNN model (3x faster)
- Reduce video resolution

## 📁 File Locations

- **Models**: `ai_model/*.pth`
- **Uploads**: `uploads/`
- **Results**: `results/`
- **Config**: `.env` (create if needed)

## 🎓 Training

```bash
# Quick train
python ai_model/train_enhanced.py --epochs 30

# Advanced train
python ai_model/train_enhanced.py --epochs 50 --use_laa --use_clip
```

## 🐳 Docker (Optional)

```bash
docker-compose up
```

## 📚 Full Docs

- **Setup**: GETTING_STARTED.md
- **Usage**: USAGE_GUIDE.md
- **Features**: README.md
- **API**: API_Documentation.md

## 💡 Pro Tips

1. Start with `quick_start.py` first time
2. Use `simple_demo.py` for testing
3. Use web interface for production
4. Save results - they're in `results/` folder
5. Test with small videos first

## ⚡ Fastest Way to Get Started

```bash
# 1. Install (wait 5-10 min)
pip install -r requirements.txt

# 2. Test it works
python simple_demo.py sample_video.mp4

# 3. Start using it
python api.py
```

## 🎯 Most Common Workflow

1. Start server: `python api.py`
2. Open browser: http://localhost:5000
3. Upload video
4. Get results
5. Check `results/` folder for JSON

---

**Need more help? Check GETTING_STARTED.md** 📖


