# SecureAI DeepFake Detection Model

This project implements a deepfake detection system that combines a trained model ensemble with blockchain-backed result storage. Detection is driven by an ensemble of models trained on Celeb-DF v2, fused with a learned logistic regression that weights each model by its measured value.

## 🚀 Features

- **Trained Ensemble Detection**: ResNet50 (test AUC 0.906) + ConvNeXt-Base (test AUC ~0.915) + an FFT frequency-domain detector, fused by a learned logistic ensemble (test AUC ~0.936 on Celeb-DF v2). See [Performance Benchmarks](#-performance-benchmarks) for measured numbers.
- **Face-Aware Preprocessing**: Frames are face-cropped (MTCNN with an OpenCV Haar-cascade fallback) before inference to match how the models were trained, with a safe fallback to the full frame when no face is found.
- **Blockchain Storage**: Solana smart contract for tamper-proof result storage
- **Real-time Analysis**: Web interface with drag-and-drop video analysis
- **Batch Processing**: Process multiple videos with comprehensive analytics
- **Production Infrastructure**: Redis caching, PostgreSQL database, AWS S3 cloud storage, Sentry error tracking

> **Honesty note**: CLIP zero-shot and LAA-Net were evaluated as candidate detectors but scored at or near chance (AUC ~0.49) on Celeb-DF v2, so the learned ensemble down-weights them to ≈0. They remain in the codebase as optional signals but do not meaningfully contribute to the production score.

## 🧠 Detection Techniques

### Production detectors (trained and evaluated on Celeb-DF v2):

1. **ResNet50 (supervised)**
   - Trained on Celeb-DF v2 face crops
   - Measured test AUC 0.906 / accuracy 0.834

2. **ConvNeXt-Base (supervised)**
   - Trained on Celeb-DF v2 face crops
   - Measured test AUC ~0.915

3. **FFT Frequency-Domain Detector**
   - Logistic regression over radial frequency spectra
   - Captures generation artifacts in the frequency domain

4. **Learned Logistic Ensemble**
   - Fuses the above detectors with coefficients learned on a held-out set
   - Measured test AUC ~0.936 — the production scoring path
   - Down-weights chance-level signals automatically (see note below)

### Candidate detectors retained but down-weighted:

- **CLIP zero-shot** ([repo](https://github.com/openai/CLIP)) and **LAA-Net**
  ([repo](https://github.com/YZY-stack/LAA-Net)) are included as optional signals,
  but on Celeb-DF v2 they scored at or near chance (AUC ~0.49). The learned ensemble
  assigns them near-zero weight, so they do not drive production predictions.

### Planned / not yet implemented:

- **Diffusion Model Awareness** — detecting diffusion-generation artifacts is on the
  roadmap but is **not** implemented in the current code path.
- **NVIDIA Morpheus ML monitoring** — the security module exposes a Morpheus-style
  interface, but no real Morpheus ML pipeline is wired in. Anomaly scoring currently
  uses a deterministic statistical signal derived from the detector's own confidence
  (no fabricated or random scores).

## 📊 Supported Datasets

### Advanced Benchmark Datasets:
- **Celeb-DF++**: Large-scale video deepfake benchmark (50GB+)
- **FaceForensics++**: Comprehensive face manipulation dataset
- **DF40**: Next-gen detection with 40 manipulation techniques
- **DeeperForensics-1.0**: Real-world face forgery detection
- **WildDeepfake**: Challenging real-world deepfake dataset
- **ForgeryNet**: Benchmark for forgery analysis

### Setup Advanced Datasets:
```bash
# Setup all advanced datasets
python datasets/advanced_datasets.py

# Setup specific dataset
python datasets/advanced_datasets.py celeb_df_pp
```

## 🏋️ Training Enhanced Models

### Train Models:
```bash
# Train the supervised detectors on Celeb-DF v2
python ai_model/train_enhanced.py --epochs 50 --batch_size 8
```

> Note: "diffusion-model-aware" training flags referenced in older docs are **not**
> implemented. The production ensemble is the trained ResNet50 + ConvNeXt + FFT models
> fused by `ai_model/trained_models/ensemble_weights.json`.

### Benchmark Models:
```bash
# Test enhanced models on multiple datasets
python test_enhanced_models.py --test_datasets datasets/val datasets/test

# Compare model performance
python test_enhanced_models.py --output_dir benchmark_results
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.11+
- PyTorch 2.7.1+ with CUDA support
- Rust and Cargo (for blockchain)
- Solana CLI
- Anchor Framework
- Git
- Docker (optional, for Redis)
- PostgreSQL (optional, for database storage)
- AWS Account (optional, for S3 cloud storage)

### Quick Setup
```bash
# Clone repository
git clone <repository-url>
cd SecureAI-DeepFake-Detection

# Install Python dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install CLIP for enhanced detection
pip install git+https://github.com/openai/CLIP.git

# Setup advanced datasets
python datasets/advanced_datasets.py
```

### Optional Services Setup (Production-Ready)

The application supports optional production services for enhanced performance and reliability:

#### 1. Redis (Caching)
```bash
# Using Docker (recommended)
docker run -d --name redis-secureai -p 6379:6379 redis:7-alpine

# Or install locally
# Windows: Download from https://redis.io/download
# Linux: sudo apt-get install redis-server
# macOS: brew install redis
```

#### 2. PostgreSQL (Database)
```bash
# Install PostgreSQL
# Windows: Download from https://www.postgresql.org/download/windows/
# Linux: sudo apt-get install postgresql postgresql-contrib
# macOS: brew install postgresql

# Create database and user
# See POSTGRESQL_SETUP_COMPLETE.md for detailed instructions
```

#### 3. AWS S3 (Cloud Storage)
```bash
# Configure AWS credentials in .env file
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=us-east-2
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

#### 4. Sentry (Error Tracking)
```bash
# Add Sentry DSN to .env file
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

**Note**: All services are optional. The application will work with file-based storage if services are not configured. See `ALL_SERVICES_SETUP_COMPLETE.md` for detailed setup instructions.

## 🎯 Usage

### Quick Test (Recommended)
```bash
python test_system.py
```

### Detection API
```python
from ai_model.detect import detect_fake

# Production path: 'enhanced'/'ensemble'/'full_ensemble' all route to the trained
# ensemble (ResNet50 + ConvNeXt + FFT, fused by the learned logistic weights).
result = detect_fake('path/to/video.mp4', model_type='enhanced')
print(f"Is fake: {result['is_fake']} (confidence: {result['confidence']:.2f})")
print(f"Fake probability: {result['fake_probability']:.2f}")
```

You can also call the detector directly:
```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector(use_face_crop=True)  # face-crops frames before inference
result = detector.detect('path/to/video.mp4')
print(result['ensemble_fake_probability'], result['method'])
```

### Web Interface
```bash
# Start Flask web server
python api.py

# Open browser to http://localhost:5000
# Upload videos for real-time analysis
```

### Batch Processing
```bash
# Process multiple videos
python batch_processor.py --input_dir videos/ --output_dir results/

# Generate analytics report
python batch_processor.py --generate_report
```

## 🏗️ Project Structure

```
SecureAI-DeepFake-Detection/
├── ai_model/
│   ├── enhanced_detector.py     # 🚀 Ensemble detection model
│   ├── deepfake_classifier.py   # CNN-based detection
│   ├── train_enhanced.py        # Advanced training script
│   └── detect.py               # Unified detection interface
├── database/
│   ├── db_session.py           # PostgreSQL database session
│   └── models.py               # SQLAlchemy models
├── storage/
│   └── s3_manager.py           # AWS S3 storage manager
├── monitoring/
│   ├── sentry_config.py        # Sentry error tracking
│   └── logging_config.py       # Structured logging
├── performance/
│   └── cache_manager.py        # Redis caching
├── datasets/
│   ├── advanced_datasets.py     # Dataset management
│   ├── data.yaml               # Dataset configuration
│   └── unified_deepfake/       # Combined dataset structure
├── blockchain/
│   └── programs/secure-ai-detector/  # Solana smart contract
├── secureai-guardian/          # React frontend
│   ├── components/             # React components
│   ├── services/               # Frontend services
│   └── package.json           # Frontend dependencies
├── static/templates/
│   ├── index.html              # Web interface
│   └── analytics.html          # Results dashboard
├── api.py                      # Flask REST API
├── realtime_analysis.py        # Real-time video analysis
├── batch_processor.py          # Batch video processing
├── test_enhanced_models.py     # Model benchmarking
├── requirements.txt            # Python dependencies
└── README.md
```

## 📈 Performance Benchmarks

All numbers below are **measured** on the Celeb-DF v2 test split and come from the
saved evaluation artifacts in `ai_model/trained_models/*.json`. They are honest,
reproducible results — not marketing figures.

### Model comparison (Celeb-DF v2 test set):
| Model | Test AUC | Test Accuracy | Notes |
|-------|----------|---------------|-------|
| **Learned ensemble (production)** | **~0.936** | ~0.84 | ResNet50 + ConvNeXt + FFT via learned logistic weights |
| ConvNeXt-Base | ~0.915 | ~0.84 | Trained on Celeb-DF v2 |
| ResNet50 | 0.906 | 0.834 | Trained on Celeb-DF v2 |
| CLIP zero-shot | ~0.49 | ~0.51 | **Near chance** — down-weighted by the ensemble |
| LAA-Net | ~0.49 | ~0.50 | **Near chance** — down-weighted by the ensemble |

The learned ensemble's coefficients (`ai_model/trained_models/ensemble_weights.json`)
make this explicit: `resnet50 ≈ 1.09` and `convnext ≈ 0.95` dominate, while
`clip ≈ 0.001` and `laa ≈ 0.021` are effectively ignored.

### Notes and caveats:
- Numbers are for **Celeb-DF v2** only. Performance on other datasets
  (FaceForensics++, WildDeepfake, etc.) has not been measured here and should not be
  assumed.
- ConvNeXt reached a higher *validation* AUC (~0.958) but did not beat ResNet50 on the
  *test* set, suggesting some validation/test distribution shift — which is exactly
  why the ensemble is learned on held-out scores rather than hand-tuned.

## 🔗 Blockchain Integration

### Smart Contract Deployment:
```bash
cd blockchain
anchor build
anchor deploy
```

### Store Detection Results:
```python
from integration.integrate import store_detection_result

# Store result on blockchain
tx_hash = store_detection_result(video_hash, detection_result, confidence)
print(f"Stored on blockchain: {tx_hash}")
```

## 🏭 Production Infrastructure

### Redis Caching
- **Purpose**: Performance optimization, API response caching
- **Status**: Optional but recommended for production
- **Setup**: See `QUICK_SETUP_REDIS.md` or `REDIS_SETUP_COMPLETE.md`

### PostgreSQL Database
- **Purpose**: Persistent storage for analysis results and user data
- **Status**: Optional, falls back to file-based storage
- **Setup**: See `POSTGRESQL_SETUP_COMPLETE.md` or `STEP2_POSTGRESQL_SETUP.md`

### AWS S3 Cloud Storage
- **Purpose**: Scalable cloud storage for videos and analysis results
- **Status**: Optional, falls back to local storage
- **Setup**: See `STEP3_AWS_S3_SETUP.md` or `S3_SETUP_COMPLETE.md`

### Sentry Error Tracking
- **Purpose**: Real-time error monitoring and performance tracking
- **Status**: Optional but recommended for production
- **Setup**: See `STEP4_SENTRY_SETUP.md` or `SENTRY_QUICK_SETUP.md`

**All services are optional** - the application works without them but provides enhanced features when configured.

## 🧪 Testing & Validation

### Run Comprehensive Tests:
```bash
# Test all components
python test_system.py

# Test enhanced models
python test_enhanced_models.py

# Test API endpoints
python test_api.py
```

### Validate on Custom Videos:
```bash
# Test single video
python -c "from detect import detect_fake; print(detect_fake('your_video.mp4', model_type='enhanced'))"

# Batch test directory
python batch_processor.py --input_dir your_videos/ --model_type enhanced
```

## 🤝 Contributing

### Adding New Detection Techniques:
1. Implement detector class in `enhanced_detector.py`
2. Add to `EnsembleDetector` class
3. Update training script if needed
4. Add tests in `test_enhanced_models.py`

### Adding New Datasets:
1. Add dataset handler in `datasets/advanced_datasets.py`
2. Update data loading in `train_enhanced.py`
3. Test with benchmarking script

## 📚 Research References

This implementation incorporates techniques from:
- [LAA-Net: Localized Artifact Attention Network](https://github.com/YZY-stack/LAA-Net)
- [FaceForensics++](https://github.com/ondyari/FaceForensics)
- [Celeb-DF++](https://github.com/OUC-VAS/Celeb-DF-PP)
- [CLIP: Learning Transferable Visual Models](https://github.com/openai/CLIP)
- [Diffusion Model Detection](https://github.com/xaCheng1996/DiFF)

## 📄 License

[Add license information]

---

## 🆘 Troubleshooting

### Common Issues:
- **CUDA not available**: Install PyTorch with CUDA support
- **CLIP import error**: `pip install git+https://github.com/openai/CLIP.git`
- **Dataset download failed**: Check internet connection and disk space
- **Blockchain deployment**: Use Solana Playground for easier deployment
- **Redis connection failed**: Ensure Redis is running (`docker ps` or `redis-cli ping`)
- **PostgreSQL connection failed**: Verify database credentials in `.env` file
- **S3 upload failed**: Check AWS credentials and bucket permissions
- **Sentry errors**: Verify `SENTRY_DSN` in `.env` file

### Performance Optimization:
- Use CUDA-enabled GPU for faster inference
- Reduce frame count for faster processing
- Use batch processing for multiple videos
- Enable Redis caching for faster API responses
- Use S3 for scalable cloud storage

### Production Deployment:
- **🌐 NEW TO CLOUD?**: See `CREATE_CLOUD_SERVER.md` - How to create a cloud server (DigitalOcean, AWS, etc.)
- **🐳 QUICK START**: See `DOCKER_QUICK_START.md` - Get running in 5 minutes
- **📚 GET STARTED**: See `GET_STARTED_DEPLOYMENT.md` - Complete step-by-step deployment guide
- **📖 FILES EXPLAINED**: See `DEPLOYMENT_FILES_EXPLAINED.md` - Understand what each file does
- **🚀 FULL GUIDE**: See `PRODUCTION_DEPLOYMENT_GUIDE.md` for complete production deployment guide
- **Docker Deployment**: Use `docker-compose.prod.yml` for containerized deployment
- **VPS/Cloud Deployment**: Use `deploy-production.sh` for automated server setup
- **Cloud Providers**: AWS, GCP, Azure deployment instructions included
- See `PRODUCTION_READINESS_ROADMAP.md` for production readiness checklist
- See `HTTPS_SETUP_GUIDE.md` for SSL/HTTPS configuration
- See `PRODUCTION_SETUP_COMPLETE.md` for deployment checklist
- **Windows Development**: See `WINDOWS_SERVICE_SETUP.md` for local development (NOT for production)

For more help, check the [Issues](issues) page or create a new issue.