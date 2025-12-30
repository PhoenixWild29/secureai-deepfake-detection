# 🚀 Getting Started with SecureAI DeepFake Detection

Welcome! This guide will help you get your deepfake detection system up and running quickly.

## ✅ Prerequisites

Before you start, make sure you have:

1. **Python 3.8 or higher** installed
   - Check with: `python --version` or `python3 --version`
   - Download from: https://www.python.org/downloads/

2. **Git** (already have it since you cloned the repo ✓)

3. **At least 4GB of RAM** (8GB+ recommended)

4. **(Optional) NVIDIA GPU** with CUDA for faster processing
   - CPU will work but is slower

## 📦 Quick Installation (3 Steps)

### Step 1: Install Dependencies

Open your terminal/command prompt in the project directory and run:

```bash
# For Windows
pip install -r requirements.txt

# For Linux/Mac
pip3 install -r requirements.txt
```

**Note:** This may take 5-10 minutes as it downloads PyTorch and other libraries.

### Step 2: Verify Installation

Run the quick start script:

```bash
python quick_start.py
```

This will:
- ✓ Check all dependencies
- ✓ Verify your trained models are present
- ✓ Create necessary folders
- ✓ Show you what to do next

### Step 3: Start Using It!

Choose one of these options:

#### Option A: Simple Demo (Test on a Video)

```bash
python simple_demo.py path/to/your/video.mp4
```

Or just run `python simple_demo.py` and select from available test videos.

#### Option B: Web Interface (Recommended for Multiple Users)

```bash
python api.py
```

Then open your browser to: **http://localhost:5000**

You'll see a beautiful web interface where you can:
- 📤 Upload videos by drag & drop
- 📊 View results in real-time
- 📈 See analytics and history
- 🔗 Share results with others

## 🎯 Your First Detection

### Quick Test with Sample Video

If you have `sample_video.mp4` in your project folder:

```bash
python simple_demo.py sample_video.mp4
```

You'll see output like:

```
🎯 SecureAI DeepFake Detection - Simple Demo
======================================================================

📹 Analyzing video: sample_video.mp4
📊 File size: 5.23 MB

🔄 Starting analysis...
   This may take 30 seconds to 2 minutes depending on video length...

======================================================================
✓ ANALYSIS COMPLETE
======================================================================

✓ VERDICT: AUTHENTIC VIDEO
   Authenticity: 87.3%

📊 Details:
   Method: ResNet50
   Processing time: 12.45 seconds
   Video hash: a3f5c9d8e2b1f4a7...
   Frames analyzed: 150

======================================================================
```

### Using the Web Interface

1. Start the server:
   ```bash
   python api.py
   ```

2. Open browser to: http://localhost:5000

3. You'll see a clean interface with:
   - **Upload Area** - Drag & drop your video
   - **Results Panel** - Shows detection results
   - **History** - View past analyses
   - **Statistics** - See your usage stats

4. Upload a video and watch the magic happen! 🎬

## 📁 Project Structure

Here's what you have:

```
SecureAI-DeepFake-Detection/
├── 📄 quick_start.py          # Interactive startup script
├── 📄 simple_demo.py          # Quick testing script
├── 📄 api.py                  # Web server (Flask)
│
├── 🤖 ai_model/               # AI Detection Models
│   ├── detect.py              # Main detection logic
│   ├── deepfake_classifier.py # CNN classifier
│   ├── enhanced_detector.py   # Advanced SOTA models
│   ├── *.pth                  # Trained model weights ✓
│   └── *.pt                   # YOLO models ✓
│
├── 🎨 templates/              # Web interface HTML
│   └── index.html             # Main UI
│
├── 📤 uploads/                # Uploaded videos go here
├── 📊 results/                # Analysis results saved here
│
└── 📚 Documentation/
    ├── README.md              # Main documentation
    ├── GETTING_STARTED.md     # This file!
    └── API_Documentation.md   # API reference
```

## 🔧 Common Issues & Solutions

### Issue 1: "Module not found" errors

**Solution:** Make sure you installed all dependencies:
```bash
pip install -r requirements.txt
```

### Issue 2: "CUDA not available" warning

**Solution:** This is OK! The system will use CPU. It's just slower.
- If you have an NVIDIA GPU, install CUDA from: https://pytorch.org/

### Issue 3: Port 5000 already in use

**Solution:** Stop other programs using port 5000, or change the port:
```python
# In api.py, change the last line:
app.run(debug=True, host='0.0.0.0', port=5001)  # Use 5001 instead
```

### Issue 4: Video upload fails

**Solution:** Check that:
- Video file is under 500MB
- Format is supported: .mp4, .avi, .mov, .mkv, .webm
- You have enough disk space

### Issue 5: Detection takes too long

**Solution:** 
- This is normal for CPU processing (can take 1-2 minutes per video)
- Use a GPU for 5-10x faster processing
- Reduce video length/quality for faster testing

## 🎓 Understanding the Results

When you analyze a video, you get:

### Key Metrics

1. **Verdict**: AUTHENTIC or DEEPFAKE
   - Based on AI analysis of facial features and artifacts

2. **Confidence Score**: 0-100%
   - How confident the AI is in its decision
   - >80% = High confidence
   - 50-80% = Medium confidence
   - <50% = Low confidence (review manually)

3. **Authenticity Score**: 0-100%
   - Inverse of confidence (for authentic videos)
   - Higher = More likely to be real

4. **Method**: Which AI model was used
   - ResNet50: Most reliable, CNN-based
   - Enhanced: SOTA ensemble model
   - CNN: Faster, basic classifier

### What to Do with Results

- **High Confidence (>80%)**: Trust the result
- **Medium Confidence (50-80%)**: Consider additional verification
- **Low Confidence (<50%)**: Video quality may be too low, or it's edge case

## 🚀 Next Steps

Now that you're set up, you can:

### 1. Test with Your Own Videos
- Upload any video through the web interface
- Or use: `python simple_demo.py your_video.mp4`

### 2. Train Your Own Models (Advanced)
```bash
# Train on your own dataset
python ai_model/train_enhanced.py --epochs 50
```

### 3. Batch Process Multiple Videos
```bash
# Process a folder of videos
python batch_processor.py --input_dir videos/ --output_dir results/
```

### 4. Integrate with Your App
```python
from ai_model.detect import detect_fake

result = detect_fake('video.mp4')
if result['is_fake']:
    print("Warning: Deepfake detected!")
```

### 5. Deploy to Production
- See `DEPLOYMENT.md` for cloud deployment guides
- Use Docker: `docker-compose up`
- Deploy to AWS, Azure, or GCP

## 📞 Need Help?

### Documentation
- **README.md** - Full project documentation
- **API_Documentation.md** - API endpoints and usage
- **Technical_Documentation.md** - Deep dive into models

### Support
- Check existing documentation files
- Review code comments in key files
- Test with the simple demo first before the full web app

## 🎉 Success Checklist

You're ready when you can:

- [ ] Run `python quick_start.py` successfully
- [ ] Test a video with `python simple_demo.py video.mp4`
- [ ] Access the web interface at http://localhost:5000
- [ ] Upload and analyze a video through the web UI
- [ ] View results and understand the metrics

## 💡 Pro Tips

1. **Start Simple**: Use `simple_demo.py` to test before running the full web server

2. **Test with Known Videos**: Try videos you know are real first to calibrate your expectations

3. **Check File Sizes**: Smaller videos (< 50MB) process faster for testing

4. **Use Web Interface**: It's easier for multiple videos and has better visualization

5. **Save Results**: All results are saved in `results/` folder as JSON files

6. **Monitor Performance**: Check processing times to gauge your system capability

---

**Ready to detect deepfakes? Let's go! 🚀**

Run this to start:
```bash
python quick_start.py
```

Or dive right into testing:
```bash
python simple_demo.py sample_video.mp4
```


