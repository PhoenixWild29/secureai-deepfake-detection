# Work Order #66 Implementation Summary

## 📋 **Work Order Details**
- **Title:** Implement Upload Data Models and Helper Functions
- **Number:** 66
- **Status:** ✅ COMPLETED
- **Completion Date:** 2025-01-27

## 🎯 **Objective**
Create the supporting data models, validation functions, and utility helpers required by the upload API endpoints to ensure proper data structure, file validation, and integration with existing Core Detection Engine models.

## 📁 **Files Created**

### 1. **`src/models/upload_models.py`**
**Purpose:** Pydantic models for upload API endpoints with comprehensive validation

**Key Models:**

#### **DashboardUploadRequest Model:**
- `file: UploadFile` - Video file to upload for deepfake detection
- `user_id: Optional[UUID]` - User ID for upload tracking and quota management
- `priority: Optional[int]` - Upload priority (1-10, default: 5)
- `metadata: Optional[Dict[str, Any]]` - Additional upload metadata
- `dashboard_context: Optional[Dict[str, Any]]` - Dashboard navigation context for upload tracking
- `auto_analyze: bool` - Whether to automatically start deepfake analysis after upload
- `store_in_s3: bool` - Whether to store file in S3 for distributed access
- `validate_content: bool` - Whether to validate video content integrity
- `check_duplicates: bool` - Whether to check for duplicate files using hash

#### **DashboardUploadResponse Model:**
- `upload_id: UUID` - Unique upload identifier
- `video_id: UUID` - Associated video record ID in Core Detection Engine
- `status: UploadStatusEnum` - Upload processing status
- `message: str` - Upload status message
- `filename: str` - Original filename of uploaded video
- `file_size: int` - File size in bytes
- `file_hash: str` - File content hash for duplicate detection
- `format: str` - Detected video format
- `storage_location: str` - Storage location (local/s3)
- `s3_key: Optional[str]` - S3 object key if stored in S3
- `s3_url: Optional[str]` - S3 URL if stored in S3
- `analysis_id: Optional[UUID]` - Analysis ID if auto_analyze enabled
- `processing_time_ms: Optional[int]` - Upload processing time in milliseconds
- `validation_result: Optional[ValidationResult]` - File validation results

#### **UploadSession Model:**
- `session_id: UUID` - Unique session identifier
- `user_id: UUID` - User ID for the upload session
- `total_files: int` - Total files in session
- `completed_files: int` - Successfully completed uploads
- `failed_files: int` - Failed uploads
- `cancelled_files: int` - Cancelled uploads
- `quota_remaining: int` - Remaining upload quota in bytes
- `quota_limit: int` - Total quota limit in bytes
- `quota_used: int` - Quota used in this session
- `dashboard_context: Optional[Dict[str, Any]]` - Dashboard navigation context
- `created_at: datetime` - Session creation timestamp
- `last_activity: datetime` - Last activity timestamp
- `expires_at: Optional[datetime]` - Session expiration time
- `auto_analyze: bool` - Whether to auto-analyze uploaded files
- `store_in_s3: bool` - Whether to store files in S3

#### **UploadProgress Model:**
- `upload_id: UUID` - Upload identifier
- `session_id: UUID` - Session identifier
- `percentage: float` - Upload percentage (0-100)
- `bytes_uploaded: int` - Bytes uploaded so far
- `bytes_total: int` - Total bytes to upload
- `upload_speed: Optional[float]` - Upload speed in bytes/second
- `estimated_completion: Optional[datetime]` - Estimated completion time
- `time_elapsed: Optional[float]` - Time elapsed in seconds
- `status: UploadProgressStatusEnum` - Current progress status
- `error_message: Optional[str]` - Error message if failed
- `filename: str` - Filename being uploaded
- `file_size: int` - File size in bytes
- `started_at: datetime` - Upload start timestamp
- `updated_at: datetime` - Last update timestamp

#### **UploadProgressEvent Model:**
- `event_type: UploadEventTypeEnum` - Type of progress event
- `upload_id: UUID` - Upload identifier
- `session_id: UUID` - Session identifier
- `user_id: Optional[UUID]` - User ID for event routing
- `progress: UploadProgress` - Current progress information
- `timestamp: datetime` - Event timestamp
- `event_id: UUID` - Unique event identifier
- `dashboard_context: Optional[Dict[str, Any]]` - Dashboard context for event routing

#### **Supporting Models:**
- `ValidationResult` - File validation result with is_valid, error_message, file_format, file_size, duration_seconds
- `S3UploadResult` - S3 upload result with success, s3_key, s3_url, error_message, upload_time_ms, file_size
- `UserQuota` - User quota model with user_id, quota_limit, quota_used, quota_remaining, last_updated
- `QuotaValidationResult` - Quota validation result with is_valid, can_upload, quota_remaining, error_message
- `UploadStatusEnum` - Upload status enumeration (PENDING, UPLOADING, VALIDATING, STORING, COMPLETED, FAILED, CANCELLED)
- `UploadProgressStatusEnum` - Progress status enumeration (STARTED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED)
- `UploadEventTypeEnum` - Event type enumeration (UPLOAD_STARTED, UPLOAD_PROGRESS, UPLOAD_COMPLETED, UPLOAD_FAILED, UPLOAD_CANCELLED)

### 2. **`src/utils/file_validation.py`**
**Purpose:** Video file validation and hash calculation functions

**Key Functions:**

#### **File Validation Functions:**
- `validate_video_file(file, max_size, validate_content)` - Comprehensive video file validation
- `validate_file_format(filename)` - Validate file format against supported extensions
- `validate_file_size(file_size, max_size)` - Validate file size against maximum limit
- `validate_file_content(file_path)` - Validate file content for video integrity using OpenCV
- `validate_mime_type(file_path, expected_formats)` - Validate file MIME type against expected formats

#### **Hash Calculation Functions:**
- `calculate_file_hash(file_path, algorithm)` - Calculate file hash for duplicate detection
- `calculate_upload_hash(upload_file)` - Calculate hash for uploaded file content

#### **Utility Functions:**
- `save_temp_file(upload_file, temp_dir)` - Save uploaded file to temporary location
- `cleanup_temp_file(file_path)` - Clean up temporary files
- `get_file_mime_type(file_path)` - Get MIME type for a file
- `get_file_info(file_path)` - Get comprehensive file information
- `batch_validate_files(files, max_size)` - Validate multiple files in batch
- `check_duplicate_files(file_hashes)` - Check for duplicate files based on hashes

#### **Constants and Configuration:**
- `SUPPORTED_VIDEO_FORMATS` - Dictionary of supported video formats and MIME types
- `MAX_FILE_SIZE` - Maximum file size (500MB as per existing configuration)
- `MIN_FILE_SIZE` - Minimum file size (1KB)
- `FileValidationError` - Custom exception for file validation errors
- `FileHashError` - Custom exception for file hash calculation errors

### 3. **`src/utils/s3_helper.py`**
**Purpose:** S3 upload helper with progress callbacks and cleanup functionality

**Key Components:**

#### **S3Helper Class:**
- `__init__(bucket_name, region_name, aws_access_key_id, aws_secret_access_key, use_ssl)` - Initialize S3 helper
- `upload_file_to_s3(file_path, s3_key, progress_callback, metadata, content_type)` - Upload file to S3 with progress tracking
- `upload_stream_to_s3(file_stream, s3_key, file_size, progress_callback, metadata, content_type)` - Upload file stream to S3 with progress tracking
- `upload_file_with_progress(file_path, s3_key, progress, metadata, content_type)` - Upload file with UploadProgress tracking
- `upload_stream_with_progress(file_stream, s3_key, file_size, progress, metadata, content_type)` - Upload stream with UploadProgress tracking
- `cleanup_failed_upload(s3_key)` - Clean up failed upload artifacts
- `cleanup_local_file(file_path)` - Clean up local temporary files
- `download_file_from_s3(s3_key, local_path, progress_callback)` - Download file from S3 with progress tracking
- `get_s3_url(s3_key, expires_in)` - Generate presigned URL for S3 object
- `object_exists(s3_key)` - Check if S3 object exists
- `get_object_size(s3_key)` - Get S3 object size
- `list_objects(prefix, max_keys)` - List objects in S3 bucket

#### **Convenience Functions:**
- `upload_file_to_s3(file_path, bucket, s3_key, progress_callback, region_name)` - Upload file to S3 (convenience function)
- `upload_stream_to_s3(file_stream, bucket, s3_key, file_size, progress_callback, region_name)` - Upload stream to S3 (convenience function)
- `cleanup_failed_upload(s3_key, bucket, region_name)` - Clean up failed upload (convenience function)
- `cleanup_local_file(file_path)` - Clean up local file (convenience function)

#### **Error Handling:**
- `S3UploadError` - Custom exception for S3 upload errors
- `S3ConfigurationError` - Custom exception for S3 configuration errors

### 4. **`src/services/quota_management.py`**
**Purpose:** User quota management with database persistence

**Key Components:**

#### **QuotaService Class:**
- `__init__(users_file, default_quota_limit, quota_reset_period_days)` - Initialize quota service
- `get_user_quota(user_id)` - Retrieve user upload quota
- `validate_upload_quota(user_id, file_size, check_multiple_files, total_files_size)` - Validate if user has sufficient quota
- `update_user_quota(user_id, bytes_used, increment)` - Update user quota after successful upload
- `reset_user_quota(user_id, quota_limit)` - Reset user quota (admin function)
- `get_user_quota_usage(user_id)` - Get detailed quota usage information
- `get_all_user_quotas()` - Get quota information for all users (admin function)
- `bulk_update_quotas(quota_updates)` - Bulk update quotas for multiple users (admin function)
- `cleanup_expired_quotas()` - Clean up expired quotas and reset them (admin function)

#### **Convenience Functions:**
- `get_user_quota(user_id, users_file)` - Retrieve user quota (convenience function)
- `validate_upload_quota(user_id, file_size, users_file)` - Validate quota (convenience function)
- `update_user_quota(user_id, bytes_used, users_file, increment)` - Update quota (convenience function)
- `reset_user_quota(user_id, quota_limit, users_file)` - Reset quota (convenience function)

#### **Error Handling:**
- `QuotaManagementError` - Custom exception for quota management errors
- `QuotaExceededError` - Custom exception when quota limit is exceeded

### 5. **Package Structure Updates**
- `src/models/__init__.py` - Updated to include upload models exports
- `src/utils/__init__.py` - Updated to include file validation and S3 helper exports
- `src/services/__init__.py` - Updated to include quota management exports

### 6. **Test Suite**
- `test_work_order_66_implementation.py` - Comprehensive test suite covering all models and requirements

## ✅ **Requirements Compliance**

### **Core Requirements Met:**

1. ✅ **DashboardUploadRequest and DashboardUploadResponse models** with all fields specified in API endpoints:
   - Complete field validation with proper data types and constraints
   - Integration with existing Core Detection Engine patterns
   - Comprehensive validation for file format, size, and metadata

2. ✅ **UploadSession model** with user ID, session ID, quota remaining, and dashboard context:
   - User ID and session ID tracking
   - Quota management with remaining and limit tracking
   - Dashboard context with JSON serialization support
   - Session lifecycle management with creation, activity, and expiration

3. ✅ **UploadProgress and UploadProgressEvent models** with percentage, bytes, speed, and completion estimates:
   - Real-time progress tracking with percentage and bytes
   - Upload speed calculation and completion time estimation
   - WebSocket compatibility for real-time updates
   - Comprehensive status tracking and error handling

4. ✅ **Video file validation function** checking format, size limits, and content validity:
   - Format validation (mp4, avi, mov, mkv, webm)
   - Size limits (500MB maximum, 1KB minimum)
   - Content validity using OpenCV for video integrity
   - MIME type validation and comprehensive file information

5. ✅ **File hash calculation function** generating consistent hashes for duplicate detection:
   - SHA256 hash calculation for file content
   - Upload file hash calculation without disk storage
   - Consistent hash generation for duplicate detection
   - Integration with existing Core Detection Engine file_hash patterns

6. ✅ **S3 upload helper** supporting progress callbacks and automatic cleanup on failures:
   - Progress callbacks for real-time upload tracking
   - Automatic cleanup on upload failures
   - Support for both file and stream uploads
   - Integration with existing S3 infrastructure patterns

7. ✅ **User quota management functions** retrieving, validating, and updating upload quotas with database persistence:
   - Quota retrieval with user management integration
   - Quota validation before upload processing
   - Quota updates with database persistence
   - Comprehensive quota usage tracking and reporting

8. ✅ **Integration with existing Core Detection Engine data models and Web Dashboard Interface patterns**:
   - Extends existing Video model with file_hash for duplicate detection
   - Uses existing S3 infrastructure and upload/download patterns
   - Follows existing Pydantic BaseModel validation patterns
   - Integrates with existing user management system

### **Out of Scope Items (Respected):**
- ❌ API endpoint implementation - covered in separate work orders
- ❌ WebSocket event handling - covered in progress tracking work order
- ❌ Core Detection Engine integration logic - covered in upload processing work order

## 🔧 **Technical Implementation Details**

### **Model Design Strategy:**

#### **Pydantic Integration:**
- **Comprehensive validation** - Field-level and model-level validation with detailed error messages
- **Type safety** - Proper Optional, List, Dict, datetime, UUID typing patterns
- **JSON serialization** - Automatic support via Pydantic for API responses
- **Extends existing patterns** - Builds on current Video model and Core Detection Engine patterns

#### **Upload Request/Response Structure:**
```python
# DashboardUploadRequest with comprehensive validation
request = DashboardUploadRequest(
    file=UploadFile("test_video.mp4"),
    user_id=UUID("..."),
    priority=5,
    metadata={"source": "dashboard"},
    dashboard_context={"current_section": "/upload"},
    auto_analyze=True,
    store_in_s3=True,
    validate_content=True,
    check_duplicates=True
)

# DashboardUploadResponse with complete upload information
response = DashboardUploadResponse(
    upload_id=UUID("..."),
    video_id=UUID("..."),
    status=UploadStatusEnum.COMPLETED,
    message="Upload completed successfully",
    filename="test_video.mp4",
    file_size=1024000,
    file_hash="abc123def456",
    format="mp4",
    storage_location="s3",
    s3_key="videos/test_video.mp4",
    analysis_id=UUID("..."),
    processing_time_ms=2500
)
```

#### **Session Management Structure:**
```python
# UploadSession with quota tracking and dashboard context
session = UploadSession(
    user_id=UUID("..."),
    quota_remaining=1000000000,  # 1GB
    quota_limit=10000000000,     # 10GB
    dashboard_context={"current_section": "/dashboard/upload"},
    auto_analyze=True,
    store_in_s3=True
)

# Session progress tracking
progress = session.get_session_progress()
# Returns: {
#   "session_id": "...",
#   "total_files": 5,
#   "completed_files": 3,
#   "failed_files": 1,
#   "completion_percentage": 60.0,
#   "quota_remaining": 500000000,
#   "quota_used": 5000000000,
#   "quota_percentage": 50.0
# }
```

#### **Progress Tracking Structure:**
```python
# UploadProgress with real-time tracking
progress = UploadProgress(
    upload_id=UUID("..."),
    session_id=UUID("..."),
    percentage=75.0,
    bytes_uploaded=750000,
    bytes_total=1000000,
    status=UploadProgressStatusEnum.IN_PROGRESS,
    filename="test_video.mp4",
    file_size=1000000
)

# Progress updates with speed calculation
progress.update_progress(800000, 1000000)  # 80% complete, 1MB/s
assert progress.percentage == 80.0
assert progress.upload_speed == 1000000
assert progress.estimated_completion is not None

# WebSocket-compatible progress events
event = UploadProgressEvent(
    event_type=UploadEventTypeEnum.UPLOAD_PROGRESS,
    upload_id=progress.upload_id,
    session_id=progress.session_id,
    user_id=UUID("..."),
    progress=progress,
    dashboard_context={"current_section": "/upload"}
)

websocket_msg = event.to_websocket_message()
# Returns WebSocket-compatible message for real-time updates
```

### **File Validation Strategy:**

#### **Comprehensive Validation Pipeline:**
```python
# Complete file validation with multiple checks
validation_result = validate_video_file(
    file=upload_file,
    max_size=500 * 1024 * 1024,  # 500MB
    validate_content=True
)

# Validation includes:
# 1. File format check (mp4, avi, mov, mkv, webm)
# 2. File size validation (1KB - 500MB)
# 3. Content integrity validation using OpenCV
# 4. MIME type validation
# 5. Hash calculation for duplicate detection

if validation_result.is_valid:
    file_hash = calculate_file_hash(temp_file_path)
    # Use hash for duplicate detection with existing Video model
```

#### **Hash Calculation for Duplicate Detection:**
```python
# File hash calculation for duplicate detection
file_hash = calculate_file_hash(file_path, algorithm="sha256")
# Returns: "a1b2c3d4e5f6..." (64-character SHA256 hash)

# Upload file hash calculation without disk storage
upload_hash = calculate_upload_hash(upload_file)
# Returns: "a1b2c3d4e5f6..." (64-character SHA256 hash)

# Integration with existing Core Detection Engine Video model
# Video.file_hash field can be used for duplicate detection
```

### **S3 Integration Strategy:**

#### **Progress-Aware Upload with Cleanup:**
```python
# S3 upload with progress tracking and cleanup
s3_helper = S3Helper(
    bucket_name="secureai-deepfake-videos",
    region_name="us-east-1"
)

# Upload with progress callback
def progress_callback(bytes_uploaded, bytes_total, speed):
    progress.update_progress(bytes_uploaded, speed)

result = await s3_helper.upload_file_to_s3(
    file_path=local_file_path,
    s3_key="videos/unique_filename.mp4",
    progress_callback=progress_callback,
    metadata={"user_id": str(user_id), "upload_timestamp": datetime.now().isoformat()},
    content_type="video/mp4"
)

if result.success:
    # Upload successful
    s3_url = result.s3_url
    s3_key = result.s3_key
else:
    # Upload failed - automatic cleanup performed
    error_message = result.error_message
    # Failed upload artifacts automatically cleaned up
```

#### **Stream Upload with Progress Tracking:**
```python
# Stream upload for large files with progress tracking
result = await s3_helper.upload_stream_to_s3(
    file_stream=upload_file,
    s3_key="videos/stream_upload.mp4",
    file_size=file_size,
    progress_callback=progress_callback,
    metadata={"upload_type": "stream"},
    content_type="video/mp4"
)
```

### **Quota Management Strategy:**

#### **Comprehensive Quota System:**
```python
# Quota service with database persistence
quota_service = QuotaService(
    users_file="users.json",  # Existing user management integration
    default_quota_limit=10 * 1024 * 1024 * 1024,  # 10GB default
    quota_reset_period_days=30
)

# Get user quota
quota = await quota_service.get_user_quota(user_id)
# Returns: UserQuota with limit, used, remaining, last_updated

# Validate upload quota
validation = await quota_service.validate_upload_quota(
    user_id=user_id,
    file_size=file_size,
    check_multiple_files=False,
    total_files_size=0
)

if validation.is_valid and validation.can_upload:
    # Proceed with upload
    pass
else:
    # Handle quota exceeded
    error_message = validation.error_message

# Update quota after successful upload
updated_quota = await quota_service.update_user_quota(
    user_id=user_id,
    bytes_used=file_size,
    increment=True
)
```

#### **Quota Usage Tracking:**
```python
# Detailed quota usage information
usage = await quota_service.get_user_quota_usage(user_id)
# Returns: {
#   "user_id": "...",
#   "quota_limit": 10737418240,
#   "quota_used": 2147483648,
#   "quota_remaining": 8589934592,
#   "usage_percentage": 20.0,
#   "last_updated": "2025-01-27T10:00:00Z",
#   "reset_date": "2025-02-26T10:00:00Z",
#   "quota_limit_gb": 10.0,
#   "quota_used_gb": 2.0,
#   "quota_remaining_gb": 8.0
# }
```

## 🎯 **Integration Points**

### **Core Detection Engine Compatibility:**
- ✅ **Extends Video model** - Uses existing file_hash field for duplicate detection
- ✅ **Integrates with existing S3** - Uses existing S3 client and upload/download functions
- ✅ **Follows existing patterns** - Uses same validation and error handling patterns
- ✅ **Database persistence** - Integrates with existing user management system
- ✅ **File validation** - Uses existing ALLOWED_EXTENSIONS and MAX_CONTENT_LENGTH patterns

### **Web Dashboard Interface Compatibility:**
- ✅ **Pydantic BaseModel** - Consistent with existing API validation patterns
- ✅ **JSON serialization** - Automatic API response compatibility
- ✅ **Field validation** - Same validation patterns as existing models
- ✅ **Error handling** - Consistent error response formats
- ✅ **Dashboard context** - Supports existing dashboard navigation patterns

### **API Integration Ready:**
- ✅ **FastAPI compatible** - Ready for FastAPI endpoint integration
- ✅ **Request/Response models** - Complete request and response model support
- ✅ **Validation ready** - Comprehensive validation for API requests
- ✅ **WebSocket support** - Progress events for real-time updates
- ✅ **Error handling** - Detailed validation error messages

## 🧪 **Testing Coverage**

### **Model Validation Tests:**
- DashboardUploadRequest creation and validation with file format checks
- DashboardUploadResponse creation with all required fields
- UploadSession creation and quota management methods
- UploadProgress creation and progress tracking methods
- UploadProgressEvent creation and WebSocket message conversion
- All supporting models (ValidationResult, S3UploadResult, UserQuota, QuotaValidationResult)

### **File Validation Tests:**
- File format validation for supported video formats
- File size validation with maximum and minimum limits
- File hash calculation for duplicate detection
- Content validation using OpenCV (with graceful fallback)
- MIME type validation and comprehensive file information
- Error handling for invalid files and missing dependencies

### **S3 Helper Tests:**
- S3Helper initialization and connection testing
- File upload with progress callbacks
- Stream upload with progress tracking
- Automatic cleanup on upload failures
- S3 object management (exists, size, list, presigned URLs)
- Error handling for S3 configuration and upload failures

### **Quota Management Tests:**
- User quota retrieval and initialization
- Quota validation for upload requests
- Quota updates after successful uploads
- Quota reset functionality (admin functions)
- Detailed quota usage reporting
- Bulk quota management operations
- Error handling for quota exceeded scenarios

### **Integration Tests:**
- UploadSession integration with quota validation
- UploadProgress integration with WebSocket events
- File validation integration with hash calculation
- S3 upload integration with progress tracking
- Complete upload workflow with all components

### **Requirements Compliance Tests:**
- All required model fields present and functional
- File validation meeting format, size, and content requirements
- Hash calculation providing consistent duplicate detection
- S3 upload helper supporting progress callbacks and cleanup
- Quota management providing retrieval, validation, and updates
- Integration with existing Core Detection Engine patterns

## 📊 **Performance Considerations**

### **Model Efficiency:**
- **Lazy loading** - Optional fields only loaded when needed
- **Efficient validation** - Field-level validation for immediate feedback
- **Memory management** - Proper handling of large file uploads
- **Progress tracking** - Efficient real-time progress updates

### **File Validation Performance:**
- **Streaming validation** - Large files validated without full memory loading
- **Hash calculation** - Efficient chunk-based hash calculation
- **Content validation** - OpenCV integration with graceful fallback
- **Batch processing** - Support for multiple file validation

### **S3 Upload Performance:**
- **Progress callbacks** - Real-time upload progress without performance impact
- **Streaming uploads** - Large files uploaded without memory constraints
- **Automatic cleanup** - Failed uploads cleaned up efficiently
- **Connection management** - Efficient S3 client connection handling

### **Quota Management Performance:**
- **Database persistence** - Efficient JSON-based quota storage
- **Validation caching** - Quota validation results cached for performance
- **Bulk operations** - Support for efficient bulk quota management
- **Expiration handling** - Automatic quota reset with minimal overhead

## 🚀 **Ready for Integration**

The implementation is complete and ready for integration with the existing SecureAI DeepFake Detection system. All components integrate seamlessly with existing Core Detection Engine patterns and provide a solid foundation for upload API endpoints.

### **Next Steps for Integration:**
1. **API Endpoint Implementation** - Create FastAPI endpoints using these models
2. **Upload Service Integration** - Connect with existing upload processing services
3. **Frontend Integration** - Use models for dashboard upload state management
4. **Progress Tracking Integration** - Connect WebSocket events with real-time updates
5. **Quota System Integration** - Connect with existing user management system

### **Usage Examples:**

#### **Complete Upload Workflow:**
```python
# 1. Validate upload request
request = DashboardUploadRequest(
    file=upload_file,
    user_id=user_id,
    priority=5,
    dashboard_context={"current_section": "/upload"}
)

# 2. Validate file
validation_result = validate_video_file(request.file)
if not validation_result.is_valid:
    raise ValueError(validation_result.error_message)

# 3. Check quota
quota_service = QuotaService()
quota_validation = await quota_service.validate_upload_quota(user_id, file_size)
if not quota_validation.can_upload:
    raise ValueError(quota_validation.error_message)

# 4. Create upload session
session = UploadSession(
    user_id=user_id,
    quota_remaining=quota_validation.quota_remaining,
    quota_limit=quota_validation.quota_remaining + file_size,
    dashboard_context=request.dashboard_context
)

# 5. Create progress tracker
progress = UploadProgress(
    upload_id=uuid4(),
    session_id=session.session_id,
    percentage=0.0,
    bytes_uploaded=0,
    bytes_total=file_size,
    status=UploadProgressStatusEnum.STARTED,
    filename=request.file.filename,
    file_size=file_size
)

# 6. Upload to S3 with progress tracking
s3_helper = S3Helper(bucket_name="secureai-deepfake-videos")
result = await s3_helper.upload_file_with_progress(
    file_path=temp_file_path,
    s3_key=f"videos/{upload_id}.mp4",
    progress=progress,
    metadata={"user_id": str(user_id)}
)

# 7. Update quota and session
if result.success:
    await quota_service.update_user_quota(user_id, file_size)
    session.mark_file_completed()
    
    response = DashboardUploadResponse(
        video_id=video_id,
        status=UploadStatusEnum.COMPLETED,
        message="Upload completed successfully",
        filename=request.file.filename,
        file_size=file_size,
        file_hash=file_hash,
        format=validation_result.file_format,
        storage_location="s3",
        s3_key=result.s3_key,
        s3_url=result.s3_url,
        processing_time_ms=result.upload_time_ms
    )
else:
    session.mark_file_failed()
    response = DashboardUploadResponse(
        video_id=video_id,
        status=UploadStatusEnum.FAILED,
        message=f"Upload failed: {result.error_message}",
        filename=request.file.filename,
        file_size=file_size,
        file_hash=file_hash,
        format=validation_result.file_format,
        storage_location="local"
    )

# 8. Send progress events for real-time updates
event = UploadProgressEvent(
    event_type=UploadEventTypeEnum.UPLOAD_COMPLETED,
    upload_id=progress.upload_id,
    session_id=session.session_id,
    user_id=user_id,
    progress=progress,
    dashboard_context=request.dashboard_context
)

websocket_msg = event.to_websocket_message()
# Send via WebSocket for real-time dashboard updates
```

---

**Implementation completed successfully with all requirements met and comprehensive testing coverage.**
