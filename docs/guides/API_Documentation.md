# SecureAI DeepFake Detection System
## Complete API Documentation

### 🔌 REST API Reference

This comprehensive API documentation covers all endpoints, authentication methods, request/response formats, and integration examples for the SecureAI DeepFake Detection System.

---

## 🚀 Quick Start

### Base URL
```
Production: https://api.secureai.com/v1
Staging: https://staging-api.secureai.com/v1
Development: https://dev-api.secureai.com/v1
```

### Authentication
All API requests require authentication using API keys or OAuth2 tokens.

```bash
# API Key Authentication
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.secureai.com/v1/detect

# OAuth2 Authentication
curl -H "Authorization: Bearer YOUR_OAUTH_TOKEN" \
     -H "Content-Type: application/json" \
     https://api.secureai.com/v1/detect
```

---

## 🔐 Authentication

### API Key Management

#### **Generate API Key**
```http
POST /auth/api-keys
```

**Request:**
```json
{
  "name": "My Application API Key",
  "permissions": [
    "video:analyze",
    "results:read",
    "dashboard:access"
  ],
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Response:**
```json
{
  "api_key": "sk_live_1234567890abcdef...",
  "key_id": "key_123456789",
  "created_at": "2025-01-27T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z",
  "permissions": [
    "video:analyze",
    "results:read",
    "dashboard:access"
  ]
}
```

#### **OAuth2 Token Exchange**
```http
POST /auth/oauth/token
```

**Request:**
```json
{
  "grant_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "scope": "video:analyze results:read"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "video:analyze results:read"
}
```

---

## 🎥 Video Analysis API

### **Single Video Analysis**

#### **Upload and Analyze Video**
```http
POST /analyze/video
```

**Request:**
```bash
curl -X POST https://api.secureai.com/v1/analyze/video \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "video=@video.mp4" \
  -F "analysis_type=comprehensive" \
  -F "options={\"detailed_forensics\": true, \"blockchain_logging\": true}"
```

**Request Parameters:**
- `video` (file, required): Video file to analyze
- `analysis_type` (string, optional): Type of analysis
  - `quick` (default): Fast analysis with basic results
  - `comprehensive`: Detailed analysis with forensic data
  - `security_focused`: Enhanced security analysis
- `options` (JSON, optional): Additional analysis options

**Response:**
```json
{
  "analysis_id": "analysis_123456789",
  "status": "completed",
  "created_at": "2025-01-27T10:30:00Z",
  "completed_at": "2025-01-27T10:31:15Z",
  "processing_time_ms": 75000,
  "results": {
    "is_deepfake": true,
    "confidence": 0.97,
    "risk_level": "high",
    "detection_techniques": [
      {
        "technique": "facial_landmark_analysis",
        "confidence": 0.95,
        "description": "Inconsistent facial landmarks detected"
      },
      {
        "technique": "temporal_consistency",
        "confidence": 0.89,
        "description": "Temporal inconsistencies in video frames"
      }
    ],
    "forensic_data": {
      "frame_analysis": {
        "total_frames": 4500,
        "anomalous_frames": 23,
        "suspicious_frames": [45, 67, 89, 123, 156]
      },
      "audio_analysis": {
        "voice_cloning_detected": true,
        "synthetic_voice_confidence": 0.87,
        "acoustic_anomalies": 12
      },
      "metadata_analysis": {
        "creation_tool_detected": "DeepFaceLab",
        "manipulation_indicators": 8,
        "compression_artifacts": "unusual"
      }
    },
    "blockchain_verification": {
      "transaction_hash": "0x1234567890abcdef...",
      "block_number": 123456789,
      "verification_status": "verified"
    }
  }
}
```

#### **Get Analysis Results**
```http
GET /analyze/video/{analysis_id}
```

**Response:**
```json
{
  "analysis_id": "analysis_123456789",
  "status": "completed",
  "results": {
    "is_deepfake": true,
    "confidence": 0.97,
    "detailed_results": {
      "visual_analysis": {
        "facial_landmarks": {
          "inconsistencies": 23,
          "artificial_features": 8,
          "blending_artifacts": 12
        },
        "eye_analysis": {
          "blink_pattern": "unnatural",
          "gaze_consistency": "inconsistent",
          "pupil_reflection": "artificial"
        }
      },
      "audio_analysis": {
        "voice_cloning": {
          "detected": true,
          "confidence": 0.87,
          "synthetic_indicators": 15
        },
        "acoustic_properties": {
          "frequency_anomalies": 8,
          "spectral_artifacts": 12
        }
      }
    }
  }
}
```

### **Batch Video Analysis**

#### **Analyze Multiple Videos**
```http
POST /analyze/batch
```

**Request:**
```json
{
  "videos": [
    {
      "url": "https://example.com/video1.mp4",
      "priority": "high",
      "analysis_type": "comprehensive"
    },
    {
      "url": "https://example.com/video2.mp4",
      "priority": "medium",
      "analysis_type": "quick"
    },
    {
      "file_data": "base64_encoded_video_data",
      "filename": "video3.mp4",
      "priority": "low",
      "analysis_type": "security_focused"
    }
  ],
  "options": {
    "parallel_processing": true,
    "max_concurrent": 5,
    "callback_url": "https://your-app.com/webhooks/analysis-complete"
  }
}
```

**Response:**
```json
{
  "batch_id": "batch_987654321",
  "status": "processing",
  "total_videos": 3,
  "completed_videos": 0,
  "failed_videos": 0,
  "estimated_completion": "2025-01-27T10:35:00Z",
  "videos": [
    {
      "video_id": "video_001",
      "analysis_id": "analysis_111111111",
      "status": "processing",
      "priority": "high"
    },
    {
      "video_id": "video_002",
      "analysis_id": "analysis_222222222",
      "status": "queued",
      "priority": "medium"
    },
    {
      "video_id": "video_003",
      "analysis_id": "analysis_333333333",
      "status": "queued",
      "priority": "low"
    }
  ]
}
```

#### **Get Batch Analysis Status**
```http
GET /analyze/batch/{batch_id}
```

**Response:**
```json
{
  "batch_id": "batch_987654321",
  "status": "completed",
  "total_videos": 3,
  "completed_videos": 3,
  "failed_videos": 0,
  "completed_at": "2025-01-27T10:34:30Z",
  "summary": {
    "deepfakes_detected": 2,
    "average_confidence": 0.89,
    "high_risk_videos": 1
  },
  "videos": [
    {
      "video_id": "video_001",
      "analysis_id": "analysis_111111111",
      "status": "completed",
      "results": {
        "is_deepfake": true,
        "confidence": 0.95
      }
    },
    {
      "video_id": "video_002",
      "analysis_id": "analysis_222222222",
      "status": "completed",
      "results": {
        "is_deepfake": false,
        "confidence": 0.98
      }
    },
    {
      "video_id": "video_003",
      "analysis_id": "analysis_333333333",
      "status": "completed",
      "results": {
        "is_deepfake": true,
        "confidence": 0.87
      }
    }
  ]
}
```

---

## 📊 Analytics & Reporting API

### **Analytics Dashboard Data**

#### **Get Analytics Overview**
```http
GET /analytics/overview
```

**Query Parameters:**
- `date_range` (string): Date range for analytics
  - `last_24h`, `last_7d`, `last_30d`, `last_90d`, `custom`
- `start_date` (ISO 8601): Start date for custom range
- `end_date` (ISO 8601): End date for custom range
- `group_by` (string): Grouping granularity
  - `hour`, `day`, `week`, `month`

**Example Request:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.secureai.com/v1/analytics/overview?date_range=last_30d&group_by=day"
```

**Response:**
```json
{
  "date_range": {
    "start_date": "2024-12-28T00:00:00Z",
    "end_date": "2025-01-27T23:59:59Z"
  },
  "summary": {
    "total_videos_analyzed": 15420,
    "deepfakes_detected": 1247,
    "detection_rate": 0.0809,
    "average_confidence": 0.92,
    "average_processing_time_ms": 1250
  },
  "trends": {
    "daily_analysis": [
      {
        "date": "2025-01-01",
        "videos_analyzed": 523,
        "deepfakes_detected": 42,
        "average_confidence": 0.91
      },
      {
        "date": "2025-01-02",
        "videos_analyzed": 487,
        "deepfakes_detected": 38,
        "average_confidence": 0.93
      }
    ]
  },
  "detection_breakdown": {
    "by_confidence": {
      "high_confidence": 892,
      "medium_confidence": 267,
      "low_confidence": 88
    },
    "by_technique": {
      "facial_landmark_analysis": 456,
      "temporal_consistency": 321,
      "voice_cloning_detection": 234,
      "metadata_analysis": 123
    }
  }
}
```

#### **Get Detailed Analytics**
```http
GET /analytics/detailed
```

**Response:**
```json
{
  "performance_metrics": {
    "processing_speed": {
      "average_ms": 1250,
      "p95_ms": 2100,
      "p99_ms": 3500,
      "max_ms": 5000
    },
    "accuracy_metrics": {
      "overall_accuracy": 0.95,
      "precision": 0.97,
      "recall": 0.93,
      "f1_score": 0.95
    },
    "system_availability": {
      "uptime_percentage": 99.9,
      "total_downtime_minutes": 43.2,
      "incident_count": 2
    }
  },
  "usage_statistics": {
    "api_calls": {
      "total": 125430,
      "successful": 124987,
      "failed": 443,
      "rate_limited": 12
    },
    "bandwidth_usage": {
      "total_gb": 15420.5,
      "average_per_video_mb": 1024.7,
      "peak_hourly_gb": 125.3
    }
  }
}
```

### **Report Generation**

#### **Generate Custom Report**
```http
POST /reports/generate
```

**Request:**
```json
{
  "report_type": "custom",
  "title": "Monthly Security Analysis Report",
  "date_range": {
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z"
  },
  "sections": [
    "executive_summary",
    "detection_statistics",
    "threat_analysis",
    "performance_metrics",
    "recommendations"
  ],
  "filters": {
    "confidence_threshold": 0.85,
    "risk_levels": ["high", "medium"],
    "analysis_types": ["comprehensive", "security_focused"]
  },
  "format": "pdf",
  "include_charts": true
}
```

**Response:**
```json
{
  "report_id": "report_456789123",
  "status": "generating",
  "estimated_completion": "2025-01-27T10:35:00Z",
  "download_url": null
}
```

#### **Get Report Status**
```http
GET /reports/{report_id}
```

**Response:**
```json
{
  "report_id": "report_456789123",
  "status": "completed",
  "created_at": "2025-01-27T10:30:00Z",
  "completed_at": "2025-01-27T10:32:15Z",
  "download_url": "https://api.secureai.com/v1/reports/download/report_456789123",
  "expires_at": "2025-02-27T10:32:15Z",
  "file_size_mb": 2.4,
  "pages": 15
}
```

---

## 🔧 Configuration API

### **System Configuration**

#### **Get System Configuration**
```http
GET /config/system
```

**Response:**
```json
{
  "detection_settings": {
    "default_analysis_type": "comprehensive",
    "confidence_threshold": 0.85,
    "processing_priority": "balanced",
    "max_file_size_mb": 500,
    "supported_formats": ["mp4", "avi", "mov", "mkv", "webm"]
  },
  "security_settings": {
    "api_rate_limits": {
      "requests_per_minute": 100,
      "requests_per_hour": 1000,
      "requests_per_day": 10000
    },
    "authentication": {
      "api_key_expiration_days": 365,
      "oauth_token_expiration_hours": 24,
      "mfa_required": true
    }
  },
  "blockchain_settings": {
    "enabled": true,
    "network": "mainnet",
    "auto_logging": true,
    "verification_required": true
  }
}
```

#### **Update System Configuration**
```http
PUT /config/system
```

**Request:**
```json
{
  "detection_settings": {
    "confidence_threshold": 0.90,
    "processing_priority": "high_accuracy"
  },
  "security_settings": {
    "api_rate_limits": {
      "requests_per_minute": 150
    }
  }
}
```

### **User Configuration**

#### **Get User Settings**
```http
GET /config/user
```

**Response:**
```json
{
  "user_id": "user_123456789",
  "preferences": {
    "default_analysis_type": "comprehensive",
    "notification_settings": {
      "email_notifications": true,
      "webhook_notifications": true,
      "sms_notifications": false
    },
    "dashboard_settings": {
      "default_date_range": "last_30d",
      "auto_refresh_interval": 300
    }
  },
  "permissions": [
    "video:analyze",
    "results:read",
    "dashboard:access",
    "reports:generate"
  ],
  "quotas": {
    "monthly_analysis_limit": 10000,
    "analyses_used_this_month": 3420,
    "remaining_analyses": 6580
  }
}
```

---

## 🔔 Webhooks & Real-time Updates

### **Webhook Configuration**

#### **Create Webhook**
```http
POST /webhooks
```

**Request:**
```json
{
  "url": "https://your-app.com/webhooks/secureai",
  "events": [
    "analysis.completed",
    "analysis.failed",
    "batch.completed",
    "system.alert"
  ],
  "secret": "your_webhook_secret",
  "active": true
}
```

**Response:**
```json
{
  "webhook_id": "webhook_789123456",
  "url": "https://your-app.com/webhooks/secureai",
  "events": [
    "analysis.completed",
    "analysis.failed",
    "batch.completed",
    "system.alert"
  ],
  "created_at": "2025-01-27T10:30:00Z",
  "active": true,
  "last_delivery": null,
  "delivery_count": 0
}
```

### **Webhook Event Payloads**

#### **Analysis Completed Event**
```json
{
  "event": "analysis.completed",
  "timestamp": "2025-01-27T10:31:15Z",
  "data": {
    "analysis_id": "analysis_123456789",
    "status": "completed",
    "results": {
      "is_deepfake": true,
      "confidence": 0.97,
      "risk_level": "high"
    }
  },
  "webhook_id": "webhook_789123456"
}
```

#### **System Alert Event**
```json
{
  "event": "system.alert",
  "timestamp": "2025-01-27T10:30:00Z",
  "data": {
    "alert_type": "high_detection_rate",
    "severity": "medium",
    "message": "Unusual spike in deepfake detection rate detected",
    "metrics": {
      "detection_rate": 0.15,
      "normal_rate": 0.08,
      "time_period": "last_hour"
    }
  },
  "webhook_id": "webhook_789123456"
}
```

---

## 🚨 Error Handling

### **Error Response Format**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "video",
      "issue": "File size exceeds maximum limit of 500MB"
    },
    "request_id": "req_123456789",
    "timestamp": "2025-01-27T10:30:00Z"
  }
}
```

### **Common Error Codes**

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request parameters are invalid |
| `UNAUTHORIZED` | 401 | Authentication required or invalid |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `FILE_TOO_LARGE` | 413 | Video file exceeds size limit |
| `UNSUPPORTED_FORMAT` | 415 | Video format not supported |
| `PROCESSING_ERROR` | 500 | Internal processing error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### **Rate Limiting**
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

---

## 📚 SDKs & Libraries

### **Python SDK**
```python
from secureai import SecureAI

# Initialize client
client = SecureAI(api_key="your_api_key")

# Analyze video
result = client.analyze_video(
    video_path="video.mp4",
    analysis_type="comprehensive"
)

print(f"Deepfake detected: {result.is_deepfake}")
print(f"Confidence: {result.confidence}")
```

### **JavaScript SDK**
```javascript
const SecureAI = require('secureai');

// Initialize client
const client = new SecureAI({ apiKey: 'your_api_key' });

// Analyze video
client.analyzeVideo({
  video: 'video.mp4',
  analysisType: 'comprehensive'
}).then(result => {
  console.log(`Deepfake detected: ${result.is_deepfake}`);
  console.log(`Confidence: ${result.confidence}`);
});
```

### **cURL Examples**
```bash
# Quick analysis
curl -X POST https://api.secureai.com/v1/analyze/video \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "video=@video.mp4"

# Batch analysis
curl -X POST https://api.secureai.com/v1/analyze/batch \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"videos": [{"url": "https://example.com/video.mp4"}]}'

# Get analytics
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.secureai.com/v1/analytics/overview?date_range=last_30d"
```

---

## 🔒 Security & Best Practices

### **API Security**
- Always use HTTPS for API requests
- Store API keys securely and rotate them regularly
- Use environment variables for sensitive configuration
- Implement proper error handling and logging
- Monitor API usage and set up alerts for unusual activity

### **Rate Limiting Best Practices**
- Implement exponential backoff for retries
- Cache results when appropriate
- Use batch endpoints for multiple requests
- Monitor rate limit headers in responses

### **Data Privacy**
- Only upload videos that you have permission to analyze
- Implement proper data retention policies
- Use secure file transfer methods
- Consider data residency requirements

---

## 📞 Support

### **API Support**
- **Documentation**: https://docs.secureai.com
- **Status Page**: https://status.secureai.com
- **Support Email**: api-support@secureai.com
- **Developer Portal**: https://developers.secureai.com

### **SDK Downloads**
- **Python**: `pip install secureai`
- **JavaScript**: `npm install secureai`
- **Go**: `go get github.com/secureai/go-sdk`
- **PHP**: `composer require secureai/php-sdk`

---

*This API documentation is regularly updated. For the latest version, visit https://docs.secureai.com/api*
