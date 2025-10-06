#!/usr/bin/env python3
"""
SecureAI DeepFake Detection API - FastAPI Version
Modern async API using Pydantic schemas for video analysis, batch processing, and blockchain integration
"""
import os
import uuid
import json
import time
import hashlib
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our new schemas
from api.schemas import (
    VideoDetectionRequest,
    DetectionResponse,
    TrainingRequest,
    StatusUpdate,
    ResultUpdate
)

# Import existing detection modules
from ai_model.detect import detect_fake
from integration.integrate import submit_to_solana
from ai_model.aistore_integration import store_video_distributed, get_storage_status as get_aistore_status
from ai_model.morpheus_security import analyze_video_security, get_security_status, start_security_monitoring
from ai_model.jetson_inference import detect_video_jetson, get_jetson_stats

# Initialize FastAPI app
app = FastAPI(
    title="SecureAI DeepFake Detection API",
    description="Enterprise-grade deepfake detection with blockchain verification",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_FOLDER = Path("uploads")
RESULTS_FOLDER = Path("results")
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Global processing statistics
processing_stats = {
    'total_analyses': 0,
    'videos_processed': 0,
    'fake_detected': 0,
    'authentic_detected': 0,
    'avg_processing_time': 0.0,
    'last_updated': datetime.now().isoformat()
}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SecureAI DeepFake Detection API v2.0",
        "version": "2.0.0",
        "framework": "FastAPI",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "framework": "FastAPI"
    }

@app.post("/api/analyze", response_model=DetectionResponse)
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)  # JSON string
):
    """
    Analyze a single video for deepfakes using FastAPI with Pydantic validation
    """
    global processing_stats

    # Validate file
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file format. Allowed: MP4, AVI, MOV, MKV, WEBM")

    try:
        # Parse metadata if provided
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON")

        # Generate unique ID
        detection_id = uuid.uuid4()

        # Save file
        extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{detection_id}.{extension}"
        filepath = UPLOAD_FOLDER / unique_filename

        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Store in AIStore distributed storage
        aistore_metadata = {
            'analysis_id': str(detection_id),
            'filename': file.filename,
            'upload_timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'file_size': len(content)
        }
        aistore_result = store_video_distributed(str(filepath), aistore_metadata)

        # Start analysis
        start_time = time.time()
        result = detect_fake(str(filepath))
        processing_time = time.time() - start_time

        # Perform security analysis with Morpheus
        security_analysis = analyze_video_security(str(filepath), result)

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

        # Submit to blockchain in background
        background_tasks.add_task(submit_to_solana, result, str(detection_id))

        # Prepare response
        response_data = {
            'analysis_id': detection_id,
            'status': 'completed',
            'overall_confidence': result.get('confidence', 0.0),
            'blockchain_hash': None,  # Will be updated after blockchain submission
            'details': {
                'confidence': result.get('confidence', 0.0),
                'is_fake': result['is_fake'],
                'processing_time': round(processing_time, 2),
                'security_analysis': security_analysis,
                'file_size': len(content),
                'aistore_info': {
                    'video_hash': aistore_result['video_hash'],
                    'storage_type': aistore_result['storage_type'],
                    'distributed_urls': aistore_result['distributed_urls'] if aistore_result['stored_distributed'] else []
                }
            },
            'processing_time_ms': int(processing_time * 1000),
            'created_at': datetime.now()
        }

        # Save result
        result_file = RESULTS_FOLDER / f"{detection_id}.json"
        with open(result_file, 'w') as f:
            json.dump({
                **response_data,
                'created_at': response_data['created_at'].isoformat(),
                'analysis_id': str(response_data['analysis_id'])
            }, f, indent=2)

        return DetectionResponse(**response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/train")
async def train_model(request: TrainingRequest):
    """
    Initiate model training or fine-tuning using Pydantic validation
    """
    try:
        # Extract hyperparameters from the request
        epochs = request.hyperparameters.get('epochs', 50)
        batch_size = request.hyperparameters.get('batch_size', 16)
        learning_rate = request.hyperparameters.get('learning_rate', 0.001)
        
        # This would integrate with your training pipeline
        # For now, return a placeholder response
        return {
            "message": f"Training initiated for model type: {request.model_type}",
            "dataset_path": request.dataset_path,
            "validation_threshold": request.validation_threshold,
            "hyperparameters": request.hyperparameters,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "status": "training_started",
            "estimated_duration": f"{epochs * 30} minutes"  # Rough estimate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Get processing statistics"""
    return processing_stats

@app.get("/api/storage/status")
async def storage_status():
    """Get distributed storage status"""
    try:
        status = get_aistore_status()
        return {
            "storage_type": "AIStore",
            "status": "operational" if status else "checking",
            "distributed_nodes": status.get('nodes', 0) if status else 0,
            "total_capacity": status.get('capacity', 'unknown') if status else 'unknown'
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/security/status")
async def security_status():
    """Get cybersecurity monitoring status"""
    try:
        status = get_security_status()
        return {
            "morpheus_status": "active" if status else "inactive",
            "threats_detected": status.get('threats', 0) if status else 0,
            "monitoring_active": status.get('active', False) if status else False
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/jetson/status")
async def jetson_status():
    """Get Jetson inference status"""
    try:
        stats = get_jetson_stats()
        return {
            "jetson_available": True,
            "gpu_utilization": stats.get('gpu_util', 0),
            "memory_used": stats.get('memory_used', 0),
            "inference_ready": stats.get('ready', False)
        }
    except Exception as e:
        return {
            "jetson_available": False,
            "error": str(e)
        }

@app.post("/api/jetson/detect")
async def jetson_detect(file: UploadFile = File(...)):
    """Run detection on NVIDIA Jetson"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    try:
        # Save file temporarily
        temp_path = UPLOAD_FOLDER / f"jetson_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Run Jetson inference
        result = detect_video_jetson(str(temp_path))

        # Cleanup
        temp_path.unlink(missing_ok=True)

        return {
            "jetson_result": result,
            "inference_time": result.get('processing_time', 0),
            "device": "NVIDIA Jetson"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jetson inference failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "api_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )