#!/usr/bin/env python3
"""
SecureAI DeepFake Detection API
REST API for video analysis, batch processing, and blockchain integration
"""
import os
import uuid
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import queue
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

from ai_model.detect import detect_fake
from integration.integrate import submit_to_solana
from ai_model.aistore_integration import store_video_distributed, get_storage_status as get_aistore_status
from ai_model.morpheus_security import analyze_video_security, get_security_status, start_security_monitoring
from ai_model.jetson_inference import detect_video_jetson, get_jetson_stats

# Load environment variables
load_dotenv()

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)

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
        except:
            return {}
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
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
    global processing_stats
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

# API Routes
@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    """Analyze a single video for deepfakes"""
    global processing_stats

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400

    try:
        # Generate unique filename
        filename = secure_filename(file.filename or 'unknown.mp4')
        unique_id = str(uuid.uuid4())
        extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{unique_id}.{extension}"
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

        # Start analysis
        start_time = time.time()
        result = detect_fake(filepath)
        processing_time = time.time() - start_time

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

        # Save result
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}.json")
        with open(result_file, 'w') as f:
            json.dump(response, f, indent=2)

        # Upload result to S3 if configured
        result_s3_key = f"results/{unique_id}.json"
        upload_to_s3(result_file, S3_RESULTS_BUCKET, result_s3_key)

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    global processing_stats

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
def submit_to_blockchain():
    """Submit analysis result to blockchain"""
    data = request.get_json()

    if not data or 'analysis_id' not in data:
        return jsonify({'error': 'Analysis ID required'}), 400

    try:
        # Load analysis result
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{data['analysis_id']}.json")
        if not os.path.exists(result_file):
            return jsonify({'error': 'Analysis result not found'}), 404

        with open(result_file, 'r') as f:
            analysis_result = json.load(f)

        # Submit to Solana blockchain
        blockchain_result = submit_to_solana(
            analysis_result['result']['video_hash'],
            analysis_result['result']['authenticity_score']
        )

        return jsonify({
            'blockchain_tx': blockchain_result,
            'message': 'Analysis result submitted to blockchain successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<analysis_id>', methods=['GET'])
def download_result(analysis_id):
    """Download analysis result as JSON"""
    try:
        result_file = os.path.join(app.config['RESULTS_FOLDER'], f"{analysis_id}.json")
        if not os.path.exists(result_file):
            return jsonify({'error': 'Result not found'}), 404

        return send_file(result_file, as_attachment=True, download_name=f"analysis_{analysis_id}.json")
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
    app.run(debug=True, host='0.0.0.0', port=5000)