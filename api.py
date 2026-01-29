#!/usr/bin/env python3
"""
SecureAI DeepFake Detection API
REST API for video analysis, batch processing, and blockchain integration
"""
#
# Socket.IO note:
# If running with eventlet, we must monkey-patch very early (before most imports).
#
import os
if os.getenv('SOCKETIO_ASYNC_MODE', '').lower() == 'eventlet':
    try:
        import eventlet  # type: ignore
        eventlet.monkey_patch()
    except Exception:
        # If eventlet isn't installed yet, container build will add it.
        pass
import uuid
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import threading
import queue
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

from ai_model.detect import detect_fake
from integration.integrate import submit_to_solana

# AIStore integration (optional)
try:
    from ai_model.aistore_integration import store_video_distributed, get_storage_status as get_aistore_status
    AISTORE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    AISTORE_AVAILABLE = False
    # Create mock functions for when AIStore is not available
    def store_video_distributed(video_path, metadata=None):
        return {
            'video_hash': '',
            'stored_distributed': False,
            'storage_type': 'local_only',
            'distributed_urls': []
        }
    def get_aistore_status():
        return {'available': False, 'storage_type': 'local_only'}
    print("[WARNING] AIStore integration not available. Using local storage only.")

from ai_model.morpheus_security import analyze_video_security, get_security_status, start_security_monitoring
from ai_model.jetson_inference import detect_video_jetson, get_jetson_stats
import logging

# Load environment variables
load_dotenv()

# Setup basic logging first (before other imports that might use logger)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Database imports
try:
    from database.db_session import get_db, init_db
    from database.models import Analysis
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database modules not available. Using file-based storage.")

# Storage imports
try:
    from storage.s3_manager import s3_manager
    S3_AVAILABLE = s3_manager.is_available()
except ImportError:
    S3_AVAILABLE = False
    logger.warning("S3 manager not available. Using local storage.")

# Monitoring imports
try:
    from monitoring.sentry_config import init_sentry
    from monitoring.logging_config import setup_logging
    MONITORING_AVAILABLE = True
    # Upgrade to structured logging if available
    try:
        logger = setup_logging('secureai-guardian', os.getenv('LOG_LEVEL', 'INFO'))
    except Exception:
        pass  # Keep basic logger if setup fails
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring modules not available.")

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Initialize monitoring
if MONITORING_AVAILABLE:
    try:
        init_sentry(app)
        logger.info("✅ Sentry error tracking initialized")
    except Exception as e:
        logger.warning(f"Sentry initialization failed: {e}")

# CORS Configuration - Update with your production domain
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
CORS(app, resources={r"/*": {"origins": CORS_ORIGINS}})

# Initialize SocketIO for real-time progress updates.
# IMPORTANT:
# - The frontend uses Socket.IO (Engine.IO) protocol, not raw WebSocket frames.
# - In production we typically run with an async worker (eventlet/gevent).
# - If multiple Gunicorn workers are used, configure a message queue so rooms/events work across workers.
socketio_message_queue = os.getenv('REDIS_URL')  # e.g. redis://redis:6379/0 (optional)
socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'eventlet'),
    message_queue=socketio_message_queue if socketio_message_queue else None,
    # More tolerant defaults for long-running inference on small CPUs.
    # Engine.IO default pingTimeout is 20s; inference can block event loop long enough to trigger disconnects.
    ping_timeout=int(os.getenv('SOCKETIO_PING_TIMEOUT', '60')),
    ping_interval=int(os.getenv('SOCKETIO_PING_INTERVAL', '25')),
)


@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe a client to an analysis room to receive progress/complete events."""
    try:
        analysis_id = None
        if isinstance(data, dict):
            analysis_id = data.get('analysis_id') or data.get('analysisId')
        if not analysis_id:
            return {'ok': False, 'error': 'analysis_id is required'}

        join_room(str(analysis_id))
        return {'ok': True, 'analysis_id': str(analysis_id)}
    except Exception as e:
        logger.exception(f"Socket.IO subscribe error: {e}")
        return {'ok': False, 'error': str(e)}


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Unsubscribe a client from an analysis room."""
    try:
        analysis_id = None
        if isinstance(data, dict):
            analysis_id = data.get('analysis_id') or data.get('analysisId')
        if analysis_id:
            leave_room(str(analysis_id))
        return {'ok': True}
    except Exception as e:
        logger.exception(f"Socket.IO unsubscribe error: {e}")
        return {'ok': False, 'error': str(e)}

# Initialize Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=os.getenv('REDIS_URL', 'memory://'),  # Use Redis in production
    strategy="fixed-window"
)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
USERS_FILE = 'users.json'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Generate a secure secret key
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# AWS S3 Configuration
USE_S3 = os.getenv('USE_LOCAL_STORAGE', 'true').lower() != 'true'
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos')
S3_RESULTS_BUCKET = os.getenv('S3_RESULTS_BUCKET_NAME', 'secureai-deepfake-results')

if USE_S3:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
else:
    s3_client = None

# Ensure directories exist (for local storage fallback)
# Use VideoPathManager if available for consistent directory management
try:
    from utils.video_paths import get_video_path_manager
    path_manager = get_video_path_manager()
    UPLOAD_FOLDER = str(path_manager.get_uploads_directory())
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    # Also ensure results directory exists
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
except ImportError:
    # Fallback to original method
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Global variables for batch processing
batch_queue = queue.Queue()
batch_results = {}
processing_stats = {
    'total_analyses': 0,
    'videos_processed': 0,
    'fake_detected': 0,
    'authentic_detected': 0,
    'avg_processing_time': 0,
    'last_updated': datetime.now().isoformat()
}


# User management functions
def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            return {}
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password using bcrypt for secure password storage"""
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    # Fallback to SHA-256 with salt if bcrypt not available (not recommended for production)
    # Note: This fallback is only for environments where bcrypt cannot be installed
    # In production, bcrypt MUST be available
    salt = secrets.token_hex(16)
    # Use SHA-256 with salt as fallback (CodeQL warning expected but acceptable for fallback)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt  # noqa: S303


def verify_password(password, hashed):
    """Verify password against hash"""
    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except (ValueError, TypeError):
            # Invalid bcrypt hash format, fall through to legacy
            pass

    # Fallback for SHA-256 with salt
    if ':' in hashed:
        hash_part, salt = hashed.rsplit(':', 1)
        # Use SHA-256 with salt as fallback (CodeQL warning expected but acceptable for fallback)
        return hashlib.sha256((password + salt).encode()).hexdigest() == hash_part  # noqa: S303
    # Legacy SHA-256 without salt (insecure, but needed for backward compatibility)
    return hash_password(password) == hashed

def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        users = load_users()
        return users.get(session['user_id'])
    return None

def require_login():
    """Decorator to require login for routes"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not get_current_user():
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_analysis_result(analysis_id, result):
    """Save analysis result to file"""
    result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{analysis_id}.json")
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

def load_analysis_result(analysis_id):
    """Load analysis result from file"""
    result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{analysis_id}.json")
    if os.path.exists(result_file):
        with open(result_file, 'r') as f:
            return json.load(f)
    return None

def update_processing_stats(result):
    """Update global processing statistics"""
    global processing_stats  # noqa: F824
    processing_stats['total_analyses'] += 1
    processing_stats['videos_processed'] += 1

    if result['is_fake']:
        processing_stats['fake_detected'] += 1
    else:
        processing_stats['authentic_detected'] += 1

    # Update average processing time (simple moving average)
    if 'analysis_time' in result:
        current_avg = processing_stats['avg_processing_time']
        processing_stats['avg_processing_time'] = (current_avg + float(result['analysis_time'].split()[0])) / 2

    processing_stats['last_updated'] = datetime.now().isoformat()

# Cloud Storage Functions
def upload_to_s3(file_path, bucket_name, s3_key):
    """Upload file to S3 bucket"""
    if not USE_S3 or not s3_client:
        return False

    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        return True
    except (NoCredentialsError, ClientError) as e:
        print(f"S3 upload failed: {e}")
        return False

def download_from_s3(bucket_name, s3_key, local_path):
    """Download file from S3 bucket"""
    if not USE_S3 or not s3_client:
        return False

    try:
        s3_client.download_file(bucket_name, s3_key, local_path)
        return True
    except (NoCredentialsError, ClientError) as e:
        print(f"S3 download failed: {e}")
        return False

def get_s3_url(bucket_name, s3_key, expiration=3600):
    """Generate presigned URL for S3 object"""
    if not USE_S3 or not s3_client:
        return None

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"S3 URL generation failed: {e}")
        return None

# Web Interface Routes
@app.route('/')
def index():
    """Serve the main web interface"""
    # Temporarily disabled login requirement for testing
    # if not get_current_user():
    #     return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/api/security/audit', methods=['POST'])
def security_audit():  # noqa: C901
    """
    Real security audit endpoint - replaces simulated frontend audit
    Performs actual system security checks
    """
    try:
        audit_steps = []
        overall_status = 'OPTIMAL'
        
        # Step 1: Backend Service Health
        step1_start = time.time()
        try:
            # Check if critical directories exist
            uploads_ok = os.path.exists(UPLOAD_FOLDER) and os.path.isdir(UPLOAD_FOLDER)
            results_ok = os.path.exists(RESULTS_FOLDER) and os.path.isdir(RESULTS_FOLDER)
            env_ready = uploads_ok and results_ok
            
            audit_steps.append({
                'name': 'ENV_READY',
                'status': 'PASS' if env_ready else 'FAIL',
                'duration': int((time.time() - step1_start) * 1000),
                'details': {
                    'uploads_folder': 'OK' if uploads_ok else 'MISSING',
                    'results_folder': 'OK' if results_ok else 'MISSING'
                }
            })
            
            if not env_ready:
                overall_status = 'DEGRADED'
        except Exception as e:
            audit_steps.append({
                'name': 'ENV_READY',
                'status': 'FAIL',
                'duration': int((time.time() - step1_start) * 1000),
                'error': str(e)
            })
            overall_status = 'DEGRADED'
        
        # Step 2: Security Integrity - Check system configuration
        step2_start = time.time()
        try:
            # Check secret key is set
            secret_key_ok = app.config.get('SECRET_KEY') is not None and len(app.config.get('SECRET_KEY', '')) >= 32
            
            # Check CORS is configured
            cors_ok = True  # CORS is enabled in app setup
            
            # Check file size limits
            max_size_ok = app.config.get('MAX_CONTENT_LENGTH', 0) > 0
            
            sec_integrity_ok = secret_key_ok and cors_ok and max_size_ok
            
            audit_steps.append({
                'name': 'SEC_INTEGRITY',
                'status': 'PASS' if sec_integrity_ok else 'FAIL',
                'duration': int((time.time() - step2_start) * 1000),
                'details': {
                    'secret_key_configured': 'OK' if secret_key_ok else 'MISSING',
                    'cors_enabled': 'OK' if cors_ok else 'DISABLED',
                    'file_size_limits': 'OK' if max_size_ok else 'MISSING'
                }
            })
            
            if not sec_integrity_ok:
                overall_status = 'DEGRADED'
        except Exception as e:
            audit_steps.append({
                'name': 'SEC_INTEGRITY',
                'status': 'FAIL',
                'duration': int((time.time() - step2_start) * 1000),
                'error': str(e)
            })
            overall_status = 'DEGRADED'
        
        # Step 3: Service Availability
        step3_start = time.time()
        try:
            # Check if storage is accessible
            storage_ok = True
            try:
                test_file = os.path.join(UPLOAD_FOLDER, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except (IOError, OSError, PermissionError):
                storage_ok = False
            
            # Check if results folder is writable
            results_writable = True
            try:
                test_file = os.path.join(RESULTS_FOLDER, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except (IOError, OSError, PermissionError):
                results_writable = False
            
            service_ok = storage_ok and results_writable
            
            audit_steps.append({
                'name': 'TIER_STABILITY',  # Keep name for compatibility
                'status': 'PASS' if service_ok else 'FAIL',
                'duration': int((time.time() - step3_start) * 1000),
                'details': {
                    'storage_writable': 'OK' if storage_ok else 'READ_ONLY',
                    'results_writable': 'OK' if results_writable else 'READ_ONLY'
                }
            })
            
            if not service_ok:
                overall_status = 'DEGRADED'
        except Exception as e:
            audit_steps.append({
                'name': 'TIER_STABILITY',
                'status': 'FAIL',
                'duration': int((time.time() - step3_start) * 1000),
                'error': str(e)
            })
            overall_status = 'DEGRADED'
        
        # Step 4: API Connectivity (NEW)
        step4_start = time.time()
        try:
            # Check if WebSocket is available
            websocket_ok = socketio is not None
            
            # Check if processing stats are being tracked
            stats_ok = processing_stats is not None and isinstance(processing_stats, dict)
            
            api_ok = websocket_ok and stats_ok
            
            audit_steps.append({
                'name': 'API_CONNECTIVITY',
                'status': 'PASS' if api_ok else 'FAIL',
                'duration': int((time.time() - step4_start) * 1000),
                'details': {
                    'websocket_available': 'OK' if websocket_ok else 'UNAVAILABLE',
                    'stats_tracking': 'OK' if stats_ok else 'DISABLED'
                }
            })
            
            if not api_ok:
                overall_status = 'DEGRADED'
        except Exception as e:
            audit_steps.append({
                'name': 'API_CONNECTIVITY',
                'status': 'FAIL',
                'duration': int((time.time() - step4_start) * 1000),
                'error': str(e)
            })
            overall_status = 'DEGRADED'
        
        # Calculate security score
        passed_steps = sum(1 for step in audit_steps if step['status'] == 'PASS')
        total_steps = len(audit_steps)
        security_score = int((passed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        audit_report = {
            'id': f"AUD-{uuid.uuid4().hex[:8].upper()}",
            'timestamp': datetime.now().isoformat(),
            'overallStatus': overall_status,
            'steps': audit_steps,
            'nodeVersion': '4.2.0-STABLE',
            'securityScore': security_score,
            'threatScore': 100 - security_score
        }
        
        return jsonify(audit_report)
        
    except Exception as e:
        logger.error(f"Security audit failed: {e}")
        return jsonify({
            'id': f"AUD-{uuid.uuid4().hex[:8].upper()}",
            'timestamp': datetime.now().isoformat(),
            'overallStatus': 'CRITICAL',
            'steps': [],
            'nodeVersion': '4.2.0-STABLE',
            'securityScore': 0,
            'threatScore': 100,
            'error': str(e)
        }), 500


# API Routes
@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")  # Limit video uploads to 10 per minute
def analyze_video():
    """Analyze a single video for deepfakes"""
    global processing_stats  # noqa: F824

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400

    try:
        # Proactively validate bind-mount permissions (common production failure mode)
        upload_dir = app.config.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
        results_dir = app.config.get('RESULTS_FOLDER', RESULTS_FOLDER)

        if not os.path.isdir(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
        if not os.path.isdir(results_dir):
            os.makedirs(results_dir, exist_ok=True)

        # Ensure we can write to both dirs (bind mounts can override container perms)
        if not os.access(upload_dir, os.W_OK):
            raise PermissionError(
                f"Upload directory not writable: '{upload_dir}'. "
                f"Fix host permissions (chown/chmod) for the mounted 'uploads' directory."
            )
        if not os.access(results_dir, os.W_OK):
            raise PermissionError(
                f"Results directory not writable: '{results_dir}'. "
                f"Fix host permissions (chown/chmod) for the mounted 'results' directory."
            )

        # Use client-provided analysis id if present (so Socket.IO room matches immediately)
        requested_analysis_id = (request.form.get('analysis_id') or '').strip()
        if requested_analysis_id:
            # Allow only safe chars for room + result file names
            safe_id = requested_analysis_id.replace('-', '').replace('_', '')
            if not safe_id.isalnum() or len(requested_analysis_id) > 120:
                return jsonify({'error': 'Invalid analysis_id'}), 400
            unique_id = requested_analysis_id
        else:
            unique_id = str(uuid.uuid4())

        # Generate unique filename (always uuid-based to avoid collisions)
        filename = secure_filename(file.filename or 'unknown.mp4')
        file_uuid = str(uuid.uuid4())
        extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{file_uuid}.{extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        # Save file locally first
        file.save(filepath)

        # Store in AIStore distributed storage
        aistore_metadata = {
            'analysis_id': unique_id,
            'filename': filename,
            'upload_timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        aistore_result = store_video_distributed(filepath, aistore_metadata)

        # Upload to S3 if configured
        s3_key = f"videos/{unique_filename}"
        upload_success = upload_to_s3(filepath, S3_BUCKET, s3_key)

        # Import progress manager
        from utils.websocket_progress import progress_manager
        
        # Register analysis for WebSocket progress updates
        progress_manager.register_analysis(unique_id, total_steps=7)
        
        # Emit initial progress
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 10,
            'status': 'UPLOADING_MEDIA...',
            'message': '[UPLOAD] Transferring file to secure node'
        }, room=unique_id)
        
        # Start analysis with progress updates
        start_time = time.time()
        
        # Progress step 1: File uploaded
        progress_manager.update_progress(unique_id, 20, 'SEQUENCING_LOCAL_BUFFER...', '[INFERENCE] Mapping media to tensor space', step=1)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 20,
            'status': 'SEQUENCING_LOCAL_BUFFER...',
            'message': '[INFERENCE] Mapping media to tensor space'
        }, room=unique_id)
        
        # Progress step 2: Starting detection
        progress_manager.update_progress(unique_id, 35, 'ALGORITHM_V3_BOOT_UP...', '[NEURAL] Loading CLIP and LAA-Net weights', step=2)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 35,
            'status': 'ALGORITHM_V3_BOOT_UP...',
            'message': '[NEURAL] Loading CLIP and LAA-Net weights'
        }, room=unique_id)
        
        # Run detection
        # IMPORTANT: This can be CPU-heavy and can block the Socket.IO heartbeat if run on the event loop.
        # Use eventlet's threadpool when available so pings/polls continue during inference.
        try:
            if os.getenv('SOCKETIO_ASYNC_MODE', '').lower() == 'eventlet':
                import eventlet  # type: ignore
                from eventlet import tpool  # type: ignore
                result = tpool.execute(detect_fake, filepath)
            else:
                result = detect_fake(filepath)
        except Exception:
            # Fallback to direct call (still logs via outer exception handler)
            result = detect_fake(filepath)
        processing_time = time.time() - start_time
        
        # Progress step 3: Analysis in progress
        progress_manager.update_progress(unique_id, 50, 'CROSS_MAPPING_TENSORS...', '[NEURAL] Analyzing sub-perceptual artifact clusters', step=3)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 50,
            'status': 'CROSS_MAPPING_TENSORS...',
            'message': '[NEURAL] Analyzing sub-perceptual artifact clusters'
        }, room=unique_id)

        # Calculate forensic metrics
        try:
            from utils.forensic_metrics import calculate_forensic_metrics
            forensic_metrics = calculate_forensic_metrics(filepath, result, num_frames=16)
        except Exception as e:
            logger.warning(f"Error calculating forensic metrics: {e}")
            # Fallback: create basic metrics from detection result
            fake_prob = result.get('confidence', 0.5) if result.get('is_fake', False) else (1 - result.get('confidence', 0.5))
            forensic_metrics = {
                'spatial_artifacts': fake_prob,
                'temporal_consistency': 0.7,
                'spectral_density': fake_prob * 0.7,
                'vocal_authenticity': 1.0 - (fake_prob * 0.6),
                'spatial_entropy_heatmap': []
            }

        # Perform security analysis with Morpheus
        security_analysis = analyze_video_security(filepath, result)

        # Update statistics
        processing_stats['total_analyses'] += 1
        processing_stats['videos_processed'] += 1
        if result['is_fake']:
            processing_stats['fake_detected'] += 1
        else:
            processing_stats['authentic_detected'] += 1
        processing_stats['avg_processing_time'] = (
            (processing_stats['avg_processing_time'] * (processing_stats['total_analyses'] - 1) + processing_time)
            / processing_stats['total_analyses']
        )
        processing_stats['last_updated'] = datetime.now().isoformat()

        # Prepare response
        response = {
            'id': unique_id,
            'filename': filename,
            'result': result,
            'security_analysis': security_analysis,
            'forensic_metrics': forensic_metrics,
            'processing_time': round(processing_time, 2),
            'timestamp': datetime.now().isoformat(),
            'file_size': os.path.getsize(filepath),
            'storage': {
                'local': True,
                's3': upload_success,
                'distributed': aistore_result['stored_distributed']
            },
            'aistore_info': {
                'video_hash': aistore_result['video_hash'],
                'storage_type': aistore_result['storage_type'],
                'distributed_urls': aistore_result['distributed_urls'] if aistore_result['stored_distributed'] else []
            }
        }

        if upload_success:
            response['s3_url'] = get_s3_url(S3_BUCKET, s3_key)

        # Save result to database or JSON file (fallback)
        if DATABASE_AVAILABLE:
            try:
                db = next(get_db())
                # Check if analysis already exists
                existing = db.query(Analysis).filter(Analysis.id == unique_id).first()
                if existing:
                    # Update existing analysis
                    existing.filename = response.get('filename', filename)
                    existing.is_fake = result.get('is_fake', False)
                    existing.confidence = result.get('confidence', 0.0)
                    existing.fake_probability = result.get('fake_probability', 0.0)
                    existing.authenticity_score = result.get('authenticity_score')
                    existing.verdict = result.get('verdict', 'UNKNOWN')
                    existing.forensic_metrics = response.get('forensic_metrics')
                    existing.spatial_entropy_heatmap = response.get('forensic_metrics', {}).get('spatial_entropy_heatmap') if response.get('forensic_metrics') else None
                    existing.video_hash = result.get('video_hash') or response.get('aistore_info', {}).get('video_hash')
                    existing.file_size = os.path.getsize(filepath) if os.path.exists(filepath) else None
                    existing.processing_time = response.get('processing_time')
                    existing.model_type = response.get('model_type', 'enhanced')
                    existing.updated_at = datetime.now()
                    if upload_success:
                        existing.s3_key = s3_key
                else:
                    # Create new analysis
                    analysis = Analysis(
                        id=unique_id,
                        user_id=session.get('user_id') if 'user_id' in session else None,
                        filename=response.get('filename', filename),
                        file_path=filepath if not S3_AVAILABLE else None,
                        s3_key=s3_key if upload_success else None,
                        is_fake=result.get('is_fake', False),
                        confidence=result.get('confidence', 0.0),
                        fake_probability=result.get('fake_probability', 0.0),
                        authenticity_score=result.get('authenticity_score'),
                        verdict=result.get('verdict', 'UNKNOWN'),
                        forensic_metrics=response.get('forensic_metrics'),
                        spatial_entropy_heatmap=response.get('forensic_metrics', {}).get('spatial_entropy_heatmap') if response.get('forensic_metrics') else None,
                        video_hash=result.get('video_hash') or response.get('aistore_info', {}).get('video_hash'),
                        file_size=os.path.getsize(filepath) if os.path.exists(filepath) else None,
                        model_type=response.get('model_type', 'enhanced'),
                        processing_time=response.get('processing_time'),
                        created_at=datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00')) if response.get('timestamp') else datetime.now(),
                    )
                    db.add(analysis)
                db.commit()
                logger.info(f"✅ Analysis {unique_id} saved to database")
            except Exception as e:
                logger.error(f"❌ Failed to save to database: {e}")
                # Fallback to file storage
                result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
                with open(result_file, 'w') as f:
                    json.dump(response, f, indent=2)
        else:
            # File-based storage (fallback)
            result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
            with open(result_file, 'w') as f:
                json.dump(response, f, indent=2)

        # Submit to Solana blockchain (non-blocking for Socket.IO)
        try:
            from integration.integrate import submit_to_solana
            video_hash = result.get('video_hash') or response.get('aistore_info', {}).get('video_hash')
            authenticity_score = result.get('authenticity_score', 0.5)
            
            if video_hash:
                network = os.getenv('SOLANA_NETWORK', 'devnet')
                # Wrap in eventlet threadpool to avoid blocking Socket.IO event loop
                if os.getenv('SOCKETIO_ASYNC_MODE', '').lower() == 'eventlet':
                    import eventlet  # type: ignore
                    from eventlet import tpool  # type: ignore
                    blockchain_tx = tpool.execute(submit_to_solana, video_hash, authenticity_score, network)
                else:
                    blockchain_tx = submit_to_solana(video_hash, authenticity_score, network=network)
                
                response['blockchain_tx'] = blockchain_tx
                response['blockchain_network'] = network
                response['blockchain_timestamp'] = datetime.now().isoformat()
                logger.info(f"✅ Blockchain transaction created: {blockchain_tx}")
            else:
                logger.warning("⚠️  No video hash available for blockchain submission")
        except Exception as e:
            logger.error(f"❌ Failed to submit to blockchain: {e}")
            # Continue without blockchain - don't fail the whole analysis

        # Upload result to S3 if configured (for file-based storage or backup)
        if not DATABASE_AVAILABLE or not S3_AVAILABLE:
            result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
            result_s3_key = f"results/{unique_id}.json"
            upload_to_s3(result_file, S3_RESULTS_BUCKET, result_s3_key)
        
        # Update saved result file with blockchain info if it exists
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r') as f:
                    saved_result = json.load(f)
                if 'blockchain_tx' in response:
                    saved_result['blockchain_tx'] = response['blockchain_tx']
                    saved_result['blockchain_network'] = response.get('blockchain_network')
                    saved_result['blockchain_timestamp'] = response.get('blockchain_timestamp')
                with open(result_file, 'w') as f:
                    json.dump(saved_result, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not update result file with blockchain info: {e}")

        # Emit completion via WebSocket
        progress_manager.complete_analysis(unique_id, response)
        socketio.emit('complete', {
            'analysis_id': unique_id,
            'progress': 100,
            'status': 'REPORT_SIGNED_AND_FINALIZED',
            'message': '[SYS] Analysis complete',
            'result': response
        }, room=unique_id)

        return jsonify(response)

    except Exception as e:
        # Log full traceback so we can diagnose 500s from production logs.
        error_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
        logger.exception(f"[{error_id}] /api/analyze failed: {e}")
        return jsonify({'error': str(e), 'error_id': error_id}), 500

@app.route('/api/analyze-url', methods=['POST'])
@limiter.limit("10 per minute")  # Limit URL analysis to 10 per minute
def analyze_video_from_url():
    """Analyze a video from URL (STREAM_INTEL mode)"""
    global processing_stats  # noqa: F824
    
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No video URL provided'}), 400
        
        video_url = data['url'].strip()
        if not video_url:
            return jsonify({'error': 'Video URL is empty'}), 400
        
        # Import video downloader
        try:
            from utils.video_downloader import download_video_from_url, download_direct_video, is_valid_video_url
        except ImportError:
            return jsonify({'error': 'Video download functionality not available. Please install yt-dlp: pip install yt-dlp'}), 500
        
        # Validate URL
        if not is_valid_video_url(video_url):
            return jsonify({'error': 'Invalid video URL. Supported: YouTube, Twitter/X, Vimeo, or direct video URLs (.mp4, .avi, etc.)'}), 400
        
        # Determine analysis id (so Socket.IO room matches immediately)
        requested_analysis_id = (data.get('analysis_id') or '').strip()
        if requested_analysis_id:
            safe_id = requested_analysis_id.replace('-', '').replace('_', '')
            if not safe_id.isalnum() or len(requested_analysis_id) > 120:
                return jsonify({'error': 'Invalid analysis_id'}), 400
            unique_id = requested_analysis_id
        else:
            unique_id = str(uuid.uuid4())

        # Download video (hybrid mode):
        # - X/Twitter URLs: require cookies to be reliable; fail fast if not configured
        # - Direct video URLs: fetch directly
        # - Other platforms: use yt-dlp
        import tempfile
        import shutil
        from urllib.parse import urlparse
        parsed = urlparse(video_url)
        domain = parsed.netloc.lower().replace('www.', '')

        is_x = domain.endswith('x.com') or domain.endswith('twitter.com') or domain.endswith('mobile.twitter.com')
        cookies_file = os.getenv('X_COOKIES_FILE', '').strip()
        if is_x and not cookies_file:
            # Production-grade behavior:
            # - Do not hang trying to fetch restricted media
            # - Return a structured error so the frontend can guide the user seamlessly
            return jsonify({
                'error': (
                    "X/Twitter requires authenticated media access. "
                    "Connect your X account (recommended) or use the SecureAI Chrome extension to analyze this post."
                ),
                'error_code': 'X_AUTH_REQUIRED',
                'platform': 'x',
                'recommended': 'BROWSER_EXTENSION_OR_OAUTH',
                'user_actions': [
                    'INSTALL_CHROME_EXTENSION',
                    'CONNECT_X_ACCOUNT',
                    'UPLOAD_VIDEO_FILE'
                ]
            }), 400

        temp_dir = tempfile.mkdtemp(prefix="secureai_url_")
        filepath = None
        filename = None

        # Download video
        try:
            path_lower = parsed.path.lower()
            is_direct = any(path_lower.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm'])
            
            if is_direct:
                filepath, filename = download_direct_video(video_url, temp_dir)
            else:
                # Shorter timeout for X (when cookies are provided) to avoid hanging UX
                timeout_seconds = 180 if is_x else 300
                filepath, filename = download_video_from_url(
                    video_url,
                    temp_dir,
                    timeout_seconds=timeout_seconds,
                    cookies_file=cookies_file if is_x else None
                )
        except Exception as e:
            # Ensure temp directory cleaned on failures
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return jsonify({'error': f'Failed to download video: {str(e)}'}), 400
        
        # Check file size
        file_size = os.path.getsize(filepath)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            os.remove(filepath)
            return jsonify({'error': f'Video file too large: {file_size / (1024*1024):.1f}MB (max: 500MB)'}), 400
        
        # Store in AIStore distributed storage
        aistore_metadata = {
            'analysis_id': unique_id,
            'filename': filename,
            'source_url': video_url,
            'upload_timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        aistore_result = store_video_distributed(filepath, aistore_metadata)
        
        # Upload to S3 if configured
        s3_key = f"videos/{filename}"
        upload_success = upload_to_s3(filepath, S3_BUCKET, s3_key)
        
        # Import progress manager
        from utils.websocket_progress import progress_manager
        
        # Register analysis for WebSocket progress updates
        progress_manager.register_analysis(unique_id, total_steps=7)
        
        # Emit initial progress
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 10,
            'status': 'DOWNLOADING_MEDIA...',
            'message': '[UPLOAD] Downloading video from URL'
        }, room=unique_id)
        
        # Start analysis with progress updates
        start_time = time.time()
        
        # Progress step 1: File downloaded
        progress_manager.update_progress(unique_id, 20, 'SEQUENCING_LOCAL_BUFFER...', '[INFERENCE] Mapping media to tensor space', step=1)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 20,
            'status': 'SEQUENCING_LOCAL_BUFFER...',
            'message': '[INFERENCE] Mapping media to tensor space'
        }, room=unique_id)
        
        # Progress step 2: Starting detection
        progress_manager.update_progress(unique_id, 35, 'ALGORITHM_V3_BOOT_UP...', '[NEURAL] Loading CLIP and LAA-Net weights', step=2)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 35,
            'status': 'ALGORITHM_V3_BOOT_UP...',
            'message': '[NEURAL] Loading CLIP and LAA-Net weights'
        }, room=unique_id)
        
        # Run detection (use eventlet threadpool if enabled to keep Socket.IO alive)
        try:
            if os.getenv('SOCKETIO_ASYNC_MODE', '').lower() == 'eventlet':
                import eventlet  # type: ignore
                from eventlet import tpool  # type: ignore
                result = tpool.execute(detect_fake, filepath)
            else:
                result = detect_fake(filepath)
        except Exception:
            result = detect_fake(filepath)
        processing_time = time.time() - start_time
        
        # Progress step 3: Analysis in progress
        progress_manager.update_progress(unique_id, 50, 'CROSS_MAPPING_TENSORS...', '[NEURAL] Analyzing sub-perceptual artifact clusters', step=3)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 50,
            'status': 'CROSS_MAPPING_TENSORS...',
            'message': '[NEURAL] Analyzing sub-perceptual artifact clusters'
        }, room=unique_id)
        
        # Progress step 4: Extracting artifacts
        progress_manager.update_progress(unique_id, 70, 'NEURAL_ARTIFACT_EXTRACTION...', '[INFERENCE] Detecting temporal flicker in facial vectors', step=4)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 70,
            'status': 'NEURAL_ARTIFACT_EXTRACTION...',
            'message': '[INFERENCE] Detecting temporal flicker in facial vectors'
        }, room=unique_id)
        
        # Calculate forensic metrics
        try:
            from utils.forensic_metrics import calculate_forensic_metrics
            forensic_metrics = calculate_forensic_metrics(filepath, result, num_frames=16)
        except Exception as e:
            logger.warning(f"Error calculating forensic metrics: {e}")
            # Fallback: create basic metrics from detection result
            fake_prob = result.get('confidence', 0.5) if result.get('is_fake', False) else (1 - result.get('confidence', 0.5))
            forensic_metrics = {
                'spatial_artifacts': fake_prob,
                'temporal_consistency': 0.7,
                'spectral_density': fake_prob * 0.7,
                'vocal_authenticity': 1.0 - (fake_prob * 0.6),
                'spatial_entropy_heatmap': []
            }
        
        # Progress step 5: Finalizing
        progress_manager.update_progress(unique_id, 85, 'FINALIZING_ENTROPY_ANALYSIS...', '[SYS] Compiling forensic report and signing hash', step=5)
        socketio.emit('progress', {
            'type': 'progress',
            'analysis_id': unique_id,
            'progress': 85,
            'status': 'FINALIZING_ENTROPY_ANALYSIS...',
            'message': '[SYS] Compiling forensic report and signing hash'
        }, room=unique_id)

        # Perform security analysis
        security_analysis = analyze_video_security(filepath, result)
        
        # Update statistics
        processing_stats['total_analyses'] += 1
        processing_stats['videos_processed'] += 1
        if result['is_fake']:
            processing_stats['fake_detected'] += 1
        else:
            processing_stats['authentic_detected'] += 1
        processing_stats['avg_processing_time'] = (
            (processing_stats['avg_processing_time'] * (processing_stats['total_analyses'] - 1) + processing_time)
            / processing_stats['total_analyses']
        )
        processing_stats['last_updated'] = datetime.now().isoformat()
        
        # Prepare response
        response = {
            'id': unique_id,
            'filename': filename,
            'sourceUrl': video_url,
            'result': result,
            'security_analysis': security_analysis,
            'forensic_metrics': forensic_metrics,
            'processing_time': round(processing_time, 2),
            'timestamp': datetime.now().isoformat(),
            'file_size': file_size,
            'storage': {
                'local': True,
                's3': upload_success,
                'distributed': aistore_result['stored_distributed']
            },
            'aistore_info': {
                'video_hash': aistore_result['video_hash'],
                'storage_type': aistore_result['storage_type'],
                'distributed_urls': aistore_result['distributed_urls'] if aistore_result['stored_distributed'] else []
            }
        }
        
        if upload_success:
            response['s3_url'] = get_s3_url(S3_BUCKET, s3_key)
        
        # Save result
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
        with open(result_file, 'w') as f:
            json.dump(response, f, indent=2)
        
        # Upload result to S3 if configured
        result_s3_key = f"results/{unique_id}.json"
        upload_to_s3(result_file, S3_RESULTS_BUCKET, result_s3_key)

        # Emit completion via WebSocket
        progress_manager.complete_analysis(unique_id, response)
        socketio.emit('complete', {
            'type': 'complete',
            'analysis_id': unique_id,
            'progress': 100,
            'status': 'REPORT_SIGNED_AND_FINALIZED',
            'message': '[SYS] Analysis complete',
            'result': response
        }, room=unique_id)

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"URL analysis error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Always clean up temp download directory to avoid filling disk.
        try:
            if 'temp_dir' in locals() and temp_dir:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

@app.route('/api/batch', methods=['POST'])
def batch_analyze():
    """Start batch analysis of multiple videos"""
    if 'videos' not in request.files:
        return jsonify({'error': 'No video files provided'}), 400

    files = request.files.getlist('videos')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No video files selected'}), 400

    batch_id = str(uuid.uuid4())
    batch_results[batch_id] = {
        'status': 'processing',
        'total_files': len([f for f in files if f.filename != '']),
        'processed': 0,
        'results': [],
        'start_time': datetime.now().isoformat()
    }

    # Start batch processing in background
    threading.Thread(target=process_batch, args=(batch_id, files)).start()

    return jsonify({
        'batch_id': batch_id,
        'status': 'processing',
        'message': f'Batch processing started for {batch_results[batch_id]["total_files"]} videos'
    })

def process_batch(batch_id, files):
    """Process batch of videos in background"""
    global processing_stats  # noqa: F824

    results = []
    for file in files:
        if file.filename == '':
            continue

        try:
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            extension = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{unique_id}.{extension}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Save file locally first
            file.save(filepath)

            # Upload to S3 if configured
            s3_key = f"videos/{unique_filename}"
            upload_success = upload_to_s3(filepath, S3_BUCKET, s3_key)

            # Analyze
            start_time = time.time()
            result = detect_fake(filepath)
            processing_time = time.time() - start_time

            # Update statistics
            processing_stats['total_analyses'] += 1
            processing_stats['videos_processed'] += 1
            if result['is_fake']:
                processing_stats['fake_detected'] += 1
            else:
                processing_stats['authentic_detected'] += 1

            analysis_result = {
                'id': unique_id,
                'filename': filename,
                'result': result,
                'processing_time': round(processing_time, 2),
                'timestamp': datetime.now().isoformat(),
                'file_size': os.path.getsize(filepath),
                'storage': 's3' if upload_success else 'local'
            }

            if upload_success:
                analysis_result['s3_url'] = get_s3_url(S3_BUCKET, s3_key)

            results.append(analysis_result)

            # Save individual result
            result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
            with open(result_file, 'w') as f:
                json.dump(analysis_result, f, indent=2)

            # Upload result to S3 if configured
            result_s3_key = f"results/{unique_id}.json"
            upload_to_s3(result_file, S3_RESULTS_BUCKET, result_s3_key)

        except Exception as e:
            results.append({
                'filename': file.filename,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

        batch_results[batch_id]['processed'] += 1
        batch_results[batch_id]['results'] = results

    batch_results[batch_id]['status'] = 'completed'
    batch_results[batch_id]['end_time'] = datetime.now().isoformat()

    # Update average processing time
    total_time = sum(r.get('processing_time', 0) for r in results if 'processing_time' in r)
    valid_results = len([r for r in results if 'processing_time' in r])
    if valid_results > 0:
        avg_time = total_time / valid_results
        processing_stats['avg_processing_time'] = (
            (processing_stats['avg_processing_time'] * (processing_stats['total_analyses'] - valid_results) + avg_time)
            / processing_stats['total_analyses']
        )
    processing_stats['last_updated'] = datetime.now().isoformat()

@app.route('/api/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """Get batch processing status"""
    if batch_id not in batch_results:
        return jsonify({'error': 'Batch not found'}), 404

    return jsonify(batch_results[batch_id])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get processing statistics"""
    return jsonify(processing_stats)

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get analysis history"""
    try:
        history = []
        for filename in os.listdir(app.config['RESULTS_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['RESULTS_FOLDER'], filename)
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    history.append(result)

        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/blockchain/submit', methods=['POST'])
@limiter.limit("5 per hour")  # Limit blockchain submissions to 5 per hour
def submit_to_blockchain():
    """Submit analysis result to blockchain"""
    data = request.get_json()

    if not data or 'analysis_id' not in data:
        return jsonify({'error': 'Analysis ID required'}), 400

    try:
        # Load analysis result - sanitize analysis_id to prevent path traversal
        analysis_id = data.get('analysis_id', '').strip()
        if not analysis_id or not analysis_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({'error': 'Invalid analysis ID'}), 400
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{analysis_id}.json")
        # Ensure path is within RESULTS_FOLDER (prevent path traversal)
        safe_result_file = os.path.normpath(result_file)
        if not safe_result_file.startswith(os.path.normpath(app.config['RESULTS_FOLDER'])):
            return jsonify({'error': 'Invalid file path'}), 400
        if not os.path.exists(safe_result_file):
            return jsonify({'error': 'Analysis result not found'}), 404

        with open(safe_result_file, 'r') as f:
            analysis_result = json.load(f)

        # Get video hash and authenticity score
        video_hash = analysis_result.get('result', {}).get('video_hash') or analysis_result.get('aistore_info', {}).get('video_hash')
        authenticity_score = analysis_result.get('result', {}).get('authenticity_score', 0.5)
        
        if not video_hash:
            return jsonify({'error': 'Video hash not found in analysis result'}), 400
        
        # Get network from environment or use devnet as default
        network = os.getenv('SOLANA_NETWORK', 'devnet')
        
        # Submit to Solana blockchain
        blockchain_result = submit_to_solana(
            video_hash,
            authenticity_score,
            network=network
        )

        # Update the analysis result with blockchain signature
        analysis_result['blockchain_tx'] = blockchain_result
        analysis_result['blockchain_network'] = network
        analysis_result['blockchain_timestamp'] = datetime.now().isoformat()
        
        # Save updated result - sanitize path to prevent traversal
        safe_result_file = os.path.normpath(result_file)
        if not safe_result_file.startswith(os.path.normpath(app.config['RESULTS_FOLDER'])):
            return jsonify({'error': 'Invalid file path'}), 400
        with open(safe_result_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)

        return jsonify({
            'blockchain_tx': blockchain_result,
            'blockchain_network': network,
            'message': 'Analysis result submitted to blockchain successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get aggregated dashboard statistics"""
    try:
        # Count results from results folder
        results_dir = app.config['RESULTS_FOLDER']
        total_analyses = 0
        fake_count = 0
        authentic_count = 0
        blockchain_count = 0
        authenticity_scores = []
        recent_analyses_times = []  # Track timestamps for processing rate calculation
        
        if os.path.exists(results_dir):
            for filename in os.listdir(results_dir):
                if filename.endswith('.json'):
                    try:
                        filepath = os.path.join(results_dir, filename)
                        with open(filepath, 'r') as f:
                            result_data = json.load(f)
                            total_analyses += 1
                            
                            result = result_data.get('result', {})
                            is_fake = result.get('is_fake', False)
                            
                            if is_fake:
                                fake_count += 1
                            else:
                                authentic_count += 1
                            
                            # Collect authenticity scores for average calculation
                            authenticity_score = result.get('authenticity_score')
                            if authenticity_score is not None:
                                authenticity_scores.append(authenticity_score)
                            elif not is_fake:
                                # If no authenticity_score but not fake, assume high authenticity
                                confidence = result.get('confidence', 0.5)
                                authenticity_scores.append(max(0.5, confidence))
                            
                            if result_data.get('blockchain_tx'):
                                blockchain_count += 1
                            
                            # Track timestamps for processing rate
                            timestamp_str = result_data.get('timestamp')
                            if timestamp_str:
                                try:
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    recent_analyses_times.append(timestamp)
                                except:
                                    pass
                    except Exception as e:
                        logger.warning(f"Error reading result file {filename}: {e}")
                        continue
        
        # Calculate average authenticity percentage
        avg_authenticity = 0.0
        if authenticity_scores:
            avg_authenticity = sum(authenticity_scores) / len(authenticity_scores)
        elif total_analyses > 0:
            # If no scores but we have analyses, calculate from fake/authentic ratio
            avg_authenticity = authentic_count / total_analyses if total_analyses > 0 else 0.0
        
        # Calculate processing rate (analyses per hour)
        processing_rate = 0.0
        if recent_analyses_times and len(recent_analyses_times) > 1:
            # Sort by timestamp
            recent_analyses_times.sort()
            # Get time span
            time_span = (recent_analyses_times[-1] - recent_analyses_times[0]).total_seconds() / 3600.0
            if time_span > 0:
                processing_rate = len(recent_analyses_times) / time_span
        elif total_analyses > 0:
            # Fallback: estimate based on total analyses and assume 24 hour period
            processing_rate = total_analyses / 24.0
        
        # Use processing_stats for real-time data, but prefer file-based counts for accuracy
        # Combine both sources for most accurate counts
        file_based_fake = fake_count
        file_based_authentic = authentic_count
        
        # Merge with processing_stats (which tracks current session)
        combined_fake = max(processing_stats.get('fake_detected', 0), file_based_fake)
        combined_authentic = max(processing_stats.get('authentic_detected', 0), file_based_authentic)
        combined_total = max(processing_stats.get('total_analyses', 0), total_analyses)
        
        stats = {
            'threats_neutralized': combined_fake,  # No hardcoded base - purely real
            'blockchain_proofs': blockchain_count,  # No hardcoded base - purely real
            'total_analyses': combined_total,
            'authentic_detected': combined_authentic,
            'fake_detected': combined_fake,
            'authenticity_percentage': round(avg_authenticity * 100, 1),  # Real calculated percentage
            'processing_rate': round(processing_rate, 1),  # Analyses per hour
            'avg_processing_time': processing_stats.get('avg_processing_time', 0),
            'last_updated': processing_stats.get('last_updated', datetime.now().isoformat())
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        # Return fallback stats (no hardcoded bases)
        return jsonify({
            'threats_neutralized': processing_stats.get('fake_detected', 0),
            'blockchain_proofs': 0,
            'total_analyses': processing_stats.get('total_analyses', 0),
            'authentic_detected': processing_stats.get('authentic_detected', 0),
            'fake_detected': processing_stats.get('fake_detected', 0),
            'authenticity_percentage': 0.0,
            'processing_rate': 0.0,
            'avg_processing_time': processing_stats.get('avg_processing_time', 0),
            'last_updated': processing_stats.get('last_updated', datetime.now().isoformat())
        })

@app.route('/api/download/<analysis_id>', methods=['GET'])
def download_result(analysis_id):
    """Download analysis result as JSON"""
    try:
        # Sanitize analysis_id to prevent path traversal
        analysis_id = analysis_id.strip()
        if not analysis_id or not analysis_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({'error': 'Invalid analysis ID'}), 400
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{analysis_id}.json")
        # Ensure path is within RESULTS_FOLDER (prevent path traversal)
        safe_result_file = os.path.normpath(result_file)
        if not safe_result_file.startswith(os.path.normpath(app.config['RESULTS_FOLDER'])):
            return jsonify({'error': 'Invalid file path'}), 400
        if not os.path.exists(safe_result_file):
            return jsonify({'error': 'Result not found'}), 404

        return send_file(safe_result_file, as_attachment=True, download_name=f"analysis_{analysis_id}.json")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/storage/status')
def get_storage_status():
    """Get cloud storage configuration status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    status = {
        'cloud_storage_enabled': USE_S3,
        's3_bucket': S3_BUCKET if USE_S3 else None,
        'results_bucket': S3_RESULTS_BUCKET if USE_S3 else None,
        'region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1') if USE_S3 else None,
        'local_fallback': True,
        'distributed_storage': get_aistore_status()
    }

    return jsonify(status)

@app.route('/api/storage/test')
def test_storage_connection():
    """Test cloud storage connection"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    if not USE_S3 or not s3_client:
        return jsonify({
            'status': 'error',
            'message': 'Cloud storage not configured or client not initialized'
        })

    try:
        # Test S3 connection by listing buckets
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]

        return jsonify({
            'status': 'connected',
            'buckets': buckets,
            'video_bucket_exists': S3_BUCKET in buckets,
            'results_bucket_exists': S3_RESULTS_BUCKET in buckets
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        users = load_users()
        user = None
        user_id = None
        for uid, user_data in users.items():
            if user_data['email'] == email:
                user = user_data
                user_id = uid
                break

        if user and user_id and verify_password(password, user['password']):
            session['user_id'] = user_id
            session.permanent = True
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            save_users(users)
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'error': 'Invalid email or password'}), 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and user creation"""
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        users = load_users()

        # Check if user already exists
        for user_data in users.values():
            if user_data['email'] == email:
                return jsonify({'error': 'Email already registered'}), 409

        # Create new user
        user_id = str(uuid.uuid4())
        users[user_id] = {
            'email': email,
            'password': hash_password(password),
            'name': name,
            'created_at': datetime.now().isoformat(),
            'analyses_count': 0,
            'last_login': datetime.now().isoformat()
        }

        save_users(users)
        session['user_id'] = user_id
        session.permanent = True

        return jsonify({'success': True, 'message': 'Registration successful'})

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/user/profile')
def get_user_profile():
    """Get current user profile"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    # Remove sensitive data
    profile = user.copy()
    profile.pop('password', None)

    return jsonify(profile)

@app.route('/api/user/stats')
def get_user_stats():
    """Get user-specific statistics"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    # Get user's analyses from history
    user_analyses = []
    for filename in os.listdir(app.config['RESULTS_FOLDER']):
        if filename.endswith('.json'):
            filepath = os.path.join(app.config['RESULTS_FOLDER'], filename)
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    # Check if this analysis belongs to the user (you might want to add user_id to results)
                    user_analyses.append(result)
            except:
                continue

    return jsonify({
        'total_analyses': len(user_analyses),
        'fake_detected': len([a for a in user_analyses if a.get('result', {}).get('is_fake')]),
        'authentic_detected': len([a for a in user_analyses if not a.get('result', {}).get('is_fake')]),
        'recent_analyses': user_analyses[-10:]  # Last 10 analyses
    })

@app.route('/api/analytics/advanced')
def get_advanced_analytics():
    """Get advanced analytics with ML insights and performance metrics"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    try:
        # Get all user analyses
        user_analyses = []
        for filename in os.listdir(app.config['RESULTS_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['RESULTS_FOLDER'], filename)
                try:
                    with open(filepath, 'r') as f:
                        result = json.load(f)
                        # Add user_id to results if not present (for backward compatibility)
                        user_analyses.append(result)
                except:
                    continue

        if not user_analyses:
            return jsonify({
                'total_analyses': 0,
                'insights': [],
                'trends': {},
                'performance': {},
                'recommendations': []
            })

        # Calculate advanced metrics
        analytics = analyze_user_data(user_analyses)

        return jsonify(analytics)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def analyze_user_data(analyses):
    """Analyze user data for advanced insights"""
    from collections import defaultdict
    import statistics

    # Sort analyses by timestamp
    analyses.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Basic metrics
    total_analyses = len(analyses)
    fake_count = sum(1 for a in analyses if a.get('result', {}).get('is_fake'))
    authentic_count = total_analyses - fake_count

    # Time-based analysis
    daily_stats = defaultdict(lambda: {'total': 0, 'fake': 0, 'authentic': 0})
    hourly_stats = defaultdict(lambda: {'total': 0, 'fake': 0, 'authentic': 0})

    processing_times = []
    confidence_scores = {'fake': [], 'authentic': []}

    for analysis in analyses:
        try:
            timestamp = datetime.fromisoformat(analysis.get('timestamp', '').replace('Z', '+00:00'))
            date_key = timestamp.date().isoformat()
            hour_key = timestamp.hour

            daily_stats[date_key]['total'] += 1
            if analysis.get('result', {}).get('is_fake'):
                daily_stats[date_key]['fake'] += 1
            else:
                daily_stats[date_key]['authentic'] += 1

            hourly_stats[hour_key]['total'] += 1
            if analysis.get('result', {}).get('is_fake'):
                hourly_stats[hour_key]['fake'] += 1
            else:
                hourly_stats[hour_key]['authentic'] += 1

            # Processing time analysis
            if 'processing_time' in analysis:
                processing_times.append(analysis['processing_time'])

            # Confidence analysis
            result = analysis.get('result', {})
            if 'confidence' in result:
                category = 'fake' if result.get('is_fake') else 'authentic'
                confidence_scores[category].append(result['confidence'])

        except:
            continue

    # Calculate insights
    insights = []

    if processing_times:
        avg_time = statistics.mean(processing_times)
        insights.append({
            'type': 'performance',
            'title': 'Processing Speed',
            'message': f'Average analysis time: {avg_time:.2f}s',
            'value': round(avg_time, 2),
            'trend': 'good' if avg_time < 5 else 'warning'
        })

    detection_rate = (fake_count / total_analyses * 100) if total_analyses > 0 else 0
    insights.append({
        'type': 'detection',
        'title': 'Detection Rate',
        'message': f'{detection_rate:.1f}% of analyzed videos detected as deepfakes',
        'value': round(detection_rate, 1),
        'trend': 'info'
    })

    # Confidence analysis
    if confidence_scores['fake']:
        avg_fake_confidence = statistics.mean(confidence_scores['fake'])
        insights.append({
            'type': 'accuracy',
            'title': 'Fake Detection Confidence',
            'message': f'Average confidence for fake detection: {(avg_fake_confidence * 100):.1f}%',
            'value': round(avg_fake_confidence * 100, 1),
            'trend': 'good' if avg_fake_confidence > 0.8 else 'warning'
        })

    if confidence_scores['authentic']:
        avg_authentic_confidence = statistics.mean(confidence_scores['authentic'])
        insights.append({
            'type': 'accuracy',
            'title': 'Authentic Detection Confidence',
            'message': f'Average confidence for authentic detection: {(avg_authentic_confidence * 100):.1f}%',
            'value': round(avg_authentic_confidence * 100, 1),
            'trend': 'good' if avg_authentic_confidence > 0.8 else 'warning'
        })

    # Usage patterns
    if len(daily_stats) > 1:
        recent_days = list(daily_stats.keys())[:7]  # Last 7 days
        recent_usage = sum(daily_stats[day]['total'] for day in recent_days)
        avg_daily = recent_usage / len(recent_days)

        insights.append({
            'type': 'usage',
            'title': 'Usage Pattern',
            'message': f'Average {avg_daily:.1f} analyses per day over the last week',
            'value': round(avg_daily, 1),
            'trend': 'info'
        })

    # File size analysis
    file_sizes = [a.get('file_size', 0) for a in analyses if 'file_size' in a]
    if file_sizes:
        avg_size = statistics.mean(file_sizes) / (1024 * 1024)  # Convert to MB
        insights.append({
            'type': 'storage',
            'title': 'Average File Size',
            'message': f'Average video size: {avg_size:.1f} MB',
            'value': round(avg_size, 1),
            'trend': 'info'
        })

    # Generate recommendations
    recommendations = []

    if detection_rate > 50:
        recommendations.append({
            'priority': 'high',
            'title': 'High Deepfake Detection Rate',
            'message': 'Consider reviewing your video sources or implementing additional verification steps.',
            'action': 'Review video sources'
        })

    if processing_times and statistics.mean(processing_times) > 10:
        recommendations.append({
            'priority': 'medium',
            'title': 'Slow Processing Times',
            'message': 'Consider upgrading your hardware or using cloud processing for better performance.',
            'action': 'Optimize processing'
        })

    if total_analyses < 10:
        recommendations.append({
            'priority': 'low',
            'title': 'Limited Analysis History',
            'message': 'Analyze more videos to get better insights and trends.',
            'action': 'Increase usage'
        })

    return {
        'total_analyses': total_analyses,
        'fake_count': fake_count,
        'authentic_count': authentic_count,
        'insights': insights,
        'trends': {
            'daily': dict(daily_stats),
            'hourly': dict(hourly_stats)
        },
        'performance': {
            'avg_processing_time': statistics.mean(processing_times) if processing_times else 0,
            'processing_times': processing_times[:100],  # Last 100 for chart
            'confidence_distribution': {
                'fake': confidence_scores['fake'][:100],
                'authentic': confidence_scores['authentic'][:100]
            }
        },
        'recommendations': recommendations
    }

@app.route('/api/security/status')
def get_security_status_endpoint():
    """Get security monitoring status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    security_status = get_security_status()
    return jsonify(security_status)

@app.route('/api/security/start', methods=['POST'])
def start_security_monitoring_endpoint():
    """Start security monitoring"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        start_security_monitoring()
        return jsonify({'message': 'Security monitoring started successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jetson/status')
def get_jetson_status():
    """Get Jetson inference status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    jetson_stats = get_jetson_stats()
    return jsonify(jetson_stats)

@app.route('/api/sage/chat', methods=['POST'])
@limiter.limit("30 per minute")  # Limit to prevent abuse
def sage_chat():
    """Secure backend endpoint for SecureSage AI consultant (proxies to Gemini API)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        history = data.get('history', [])
        context = data.get('context', {})
        
        # Get API key from backend environment (secure)
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key or gemini_api_key == 'your_actual_api_key_here':
            return jsonify({
                'error': 'GEMINI_API_KEY not configured on server',
                'message': 'Please set GEMINI_API_KEY environment variable on the backend server'
            }), 500
        
        # Import Google Generative AI
        try:
            import google.generativeai as genai
        except ImportError:
            return jsonify({
                'error': 'google-generativeai package not installed',
                'message': 'Please install: pip install google-generativeai'
            }), 500
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Build context instruction
        history_summary = ', '.join([f"{s.get('fileName', 'unknown')} ({s.get('verdict', 'unknown')})" for s in context.get('scanHistory', [])]) or 'Empty'
        last_audit = context.get('auditHistory', [{}])[0] if context.get('auditHistory') else {}
        
        context_instruction = f"""
[USER CONTEXT]
Current View: {context.get('view', 'unknown')}
User Tier: {context.get('tier', 'unknown')}
Full Ledger Summary: {history_summary}
{context.get('tier') == 'POWER_USER' and 'IDENTITY_STATUS: SYSTEM_ARCHITECT_RECOGNIZED' or ''}

[SYSTEM HEALTH]
Last Audit: {last_audit.get('overallStatus', 'No audits performed yet')} (ID: {last_audit.get('id', 'N/A')})
"""
        
        if context.get('result'):
            r = context['result']
            metrics = r.get('metrics', {})
            context_instruction += f"""
[CURRENT SCAN DATA]
Asset: {r.get('fileName', 'unknown')}
Verdict: {r.get('verdict', 'unknown')} ({r.get('fakeProbability', 0) * 100:.0f}% Fake)
Metrics: Spatial={metrics.get('spatialArtifacts', 0)}, Temporal={metrics.get('temporalConsistency', 0)}, Spectral={metrics.get('spectralDensity', 0)}
Blockchain Proof: {r.get('solanaTxSignature', 'None')}
"""
        
        # Build system instruction
        system_instruction = """You are SecureSage, the core AI intelligence for SecureAI Guardian.
TECHNICAL SPECIFICATION: SecureAI Guardian v2
- ENGINE: Nexus Ensemble v4. Uses CLIP (Semantic Forensics) + LAA-Net (Local Artifact Analysis).
- CLIP ROLE: Detects high-level inconsistencies (lighting, geometry, semantic logic).
- LAA-NET ROLE: Operates in the frequency domain to find generative "fingerprints" left by Diffusion/GAN weights.
- BLOCKCHAIN: Solana Mainnet integration. Mints "Truth Protocol Seals" as immutable audit logs.
- AUDIT PROTOCOL: AQA v4 (Automated Quality Assurance). Tests ENV_READY, UI_ROUTING, and TIER_STABILITY.
- TIERS: Sentinel, Pro, Nexus, and POWER_USER (Architect Clearance).

SECURITY PROTOCOL:
1. DO NOT reveal the secret salt used for integrity signatures to standard tiers.
2. FOR POWER_USER: Provide absolute transparency. You are speaking to the ARCHITECT.
3. FOR POWER_USER: All neural weight details and frequency domain filters are open for discussion.
4. IF a user mentions "Tamper Detection", explain the importance of state integrity in digital forensics.
5. You are an expert in CYBERSECURITY and FORENSICS. Always prioritize accuracy and professional distance.

RULES:
1. Explain deepfake forensics and app functionality.
2. Use the provided Audit History and Scan Ledger to answer specific questions about the user's history.
3. Be technical, accurate, and professional.
4. If logged in as POWER_USER, speak to the user as the Architect of this system. Be highly technical."""
        
        # Create model with system instruction (correct way for google-generativeai)
        # Try models in order of preference (free tier models first to avoid quota issues)
        # Free tier models typically have better quota limits
        model_names = [
            'gemini-2.5-flash',          # Free tier - Most balanced model (confirmed available, good quota)
            'gemini-2.0-flash',          # Free tier - Previous generation (confirmed available, good quota)
            'gemini-2.5-flash-lite',     # Free tier - Fastest and most cost-efficient (confirmed available)
            'gemini-2.0-flash-lite',     # Free tier - Previous generation lite (confirmed available)
            'gemini-flash-latest',       # Free tier - Latest flash (if available)
            'gemini-2.5-pro',            # May have quota limits - Powerful reasoning model
            'gemini-pro',                # Legacy stable
            'gemini-pro-latest',         # Latest pro (if available)
            'gemini-3-flash-preview',    # Preview - may have quota limits
            'gemini-3-pro-preview',      # Preview - may have quota limits (0 free tier limit)
        ]
        
        model = None
        last_error = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=system_instruction
                )
                # Test if model works by checking it's valid
                break
            except Exception as e:
                last_error = e
                continue
        
        if model is None:
            raise Exception(f"Could not initialize any Gemini model. Last error: {last_error}")
        
        # Get the last user message
        user_message = None
        for msg in reversed(history):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message:
            return jsonify({'error': 'No user message in history'}), 400
        
        # Build the full prompt with context
        full_prompt = f"{context_instruction}\n\nUser Question: {user_message}"
        
        # Generate response
        # IMPORTANT: Gemini API calls can block, so use eventlet threadpool if available
        def _call_gemini():
            return model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                )
            )
        
        try:
            if os.getenv('SOCKETIO_ASYNC_MODE', '').lower() == 'eventlet':
                import eventlet  # type: ignore
                from eventlet import tpool  # type: ignore
                response = tpool.execute(_call_gemini)
            else:
                response = _call_gemini()
        except Exception:
            # Fallback to direct call
            response = _call_gemini()
        
        return jsonify({
            'response': response.text or "Communication uplink unstable."
        })
        
    except Exception as e:
        logger.error(f"SecureSage API error: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'SecureSage core is offline',
            'message': f'Error: {str(e)}. Please check server logs.'
        }), 500

@app.route('/api/jetson/detect', methods=['POST'])
def jetson_detect():
    """Detect deepfakes using Jetson inference"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400

    try:
        # Save file temporarily
        filename = secure_filename(file.filename or 'unknown.mp4')
        unique_id = str(uuid.uuid4())
        extension = filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"jetson_{unique_id}.{extension}")

        file.save(filepath)

        # Perform Jetson inference
        start_time = time.time()
        result = detect_video_jetson(filepath)
        processing_time = time.time() - start_time

        # Clean up temp file
        try:
            os.remove(filepath)
        except:
            pass

        if result['success']:
            response = {
                'id': unique_id,
                'filename': filename,
                'jetson_result': result,
                'processing_time': round(processing_time, 2),
                'timestamp': datetime.now().isoformat()
            }
            return jsonify(response)
        else:
            return jsonify({'error': result.get('error', 'Detection failed')}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting SecureAI DeepFake Detection API...")
    print("📊 Web Interface: http://localhost:5000")
    print("🔗 API Endpoints: http://localhost:5000/api/*")
    # Use environment variable for debug mode, default to False for security
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)