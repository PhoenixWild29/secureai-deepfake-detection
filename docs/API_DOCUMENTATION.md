# 📚 SecureAI Guardian API Documentation

## Base URL

**Development**: `http://localhost:5000`  
**Production**: `https://your-domain.com`

## Authentication

Most endpoints require authentication via session or JWT token.

### Session-Based (Current)
- Login via `/login` endpoint
- Session stored in cookies

### JWT-Based (Recommended for Production)
```
Authorization: Bearer <token>
```

---

## Endpoints

### Health Check

**GET** `/api/health`

Check API health status.

**Response:**
```json
{
  "healthy": true,
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "4.2.0"
}
```

---

### Analyze Video (File Upload)

**POST** `/api/analyze`

Analyze a video file for deepfake detection.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `video`: Video file (mp4, avi, mov, mkv, webm)
  - `model_type`: Model type (optional, default: 'enhanced')
  - `analysis_id`: Analysis ID (optional, auto-generated if not provided)

**Rate Limit:** 10 requests per minute

**Response:**
```json
{
  "id": "analysis_1234567890",
  "filename": "video.mp4",
  "result": {
    "is_fake": false,
    "confidence": 0.95,
    "fake_probability": 0.05,
    "authenticity_score": 0.95,
    "verdict": "REAL",
    "video_hash": "abc123..."
  },
  "forensic_metrics": {
    "spatial_artifacts": 0.2,
    "temporal_consistency": 0.9,
    "spectral_density": 0.15,
    "vocal_authenticity": 0.95,
    "spatial_entropy_heatmap": [...]
  },
  "processing_time": 12.5,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Error Responses:**
- `400`: Invalid file format or missing file
- `413`: File too large (>500MB)
- `429`: Rate limit exceeded
- `500`: Processing error

---

### Analyze Video (URL)

**POST** `/api/analyze-url`

Analyze a video from URL (YouTube, Twitter/X, etc.).

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "analysisType": "comprehensive",
  "modelType": "enhanced"
}
```

**Rate Limit:** 10 requests per minute

**Response:** Same as `/api/analyze`

**Error Responses:**
- `400`: Invalid URL or download failed
- `429`: Rate limit exceeded
- `500`: Processing error

---

### Dashboard Statistics

**GET** `/api/dashboard/stats`

Get aggregated dashboard statistics.

**Response:**
```json
{
  "threats_neutralized": 1429,
  "blockchain_proofs": 412,
  "total_analyses": 5000,
  "authentic_detected": 3571,
  "fake_detected": 1429,
  "authenticity_percentage": 71.4,
  "processing_rate": 12.5,
  "avg_processing_time": 15.2,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

---

### Analysis History

**GET** `/api/analyses`

Get analysis history.

**Query Parameters:**
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset (default: 0)
- `verdict`: Filter by verdict (FAKE, REAL, SUSPICIOUS)

**Response:**
```json
[
  {
    "id": "analysis_123",
    "filename": "video.mp4",
    "verdict": "REAL",
    "confidence": 0.95,
    "created_at": "2024-01-01T00:00:00Z"
  },
  ...
]
```

---

### Blockchain Submission

**POST** `/api/blockchain/submit`

Submit analysis result to Solana blockchain.

**Request:**
```json
{
  "analysis_id": "analysis_123"
}
```

**Rate Limit:** 5 requests per hour

**Response:**
```json
{
  "blockchain_tx": "transaction_signature_here",
  "blockchain_network": "devnet",
  "message": "Analysis result submitted to blockchain successfully"
}
```

---

### Security Audit

**GET** `/api/security/audit`

Run security audit of the system.

**Authentication:** Required

**Response:**
```json
{
  "id": "AUD-12345678",
  "timestamp": "2024-01-01T00:00:00Z",
  "overallStatus": "OPTIMAL",
  "steps": [
    {
      "name": "ENV_READY",
      "status": "PASS",
      "duration": 0,
      "message": "Uploads and results directories exist."
    },
    ...
  ],
  "nodeVersion": "4.2.0-STABLE",
  "securityScore": 100
}
```

---

## WebSocket Events

### Connection

Connect to: `ws://localhost:5000/socket.io/`

### Events

**Subscribe to Analysis:**
```json
{
  "type": "subscribe",
  "analysis_id": "analysis_123"
}
```

**Progress Update:**
```json
{
  "type": "progress",
  "analysis_id": "analysis_123",
  "progress": 50,
  "status": "PROCESSING",
  "message": "[SYS] Analyzing video frames..."
}
```

**Completion:**
```json
{
  "type": "complete",
  "analysis_id": "analysis_123",
  "progress": 100,
  "status": "COMPLETED",
  "result": { ... }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 413 | Payload Too Large - File exceeds size limit |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Backend not running |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/analyze` | 10/minute |
| `/api/analyze-url` | 10/minute |
| `/api/blockchain/submit` | 5/hour |
| Other endpoints | 200/hour, 50/minute |

---

## Data Models

### Analysis Result

```typescript
interface AnalysisResult {
  id: string;
  filename: string;
  source_url?: string;
  is_fake: boolean;
  confidence: number;  // 0.0 - 1.0
  fake_probability: number;  // 0.0 - 1.0
  authenticity_score: number;  // 0.0 - 1.0
  verdict: 'FAKE' | 'REAL' | 'SUSPICIOUS';
  forensic_metrics: {
    spatial_artifacts: number;
    temporal_consistency: number;
    spectral_density: number;
    vocal_authenticity: number;
    spatial_entropy_heatmap: Array<{
      sector: [number, number];
      intensity: number;
      detail: number;
    }>;
  };
  blockchain_tx?: string;
  processing_time: number;
  timestamp: string;
}
```

---

## Examples

### cURL Examples

**Health Check:**
```bash
curl http://localhost:5000/api/health
```

**Analyze Video:**
```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "video=@video.mp4" \
  -F "model_type=enhanced"
```

**Analyze from URL:**
```bash
curl -X POST http://localhost:5000/api/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=...", "analysisType": "comprehensive"}'
```

**Get Dashboard Stats:**
```bash
curl http://localhost:5000/api/dashboard/stats
```

---

## Changelog

### v4.2.0
- Added WebSocket support for real-time progress
- Added forensic metrics and spatial entropy heatmap
- Added Solana blockchain integration
- Added rate limiting
- Added security headers
- Database migration support
- S3 storage integration

---

## Support

For issues or questions:
- Check logs: `/var/log/secureai/`
- Review error responses for details
- Check rate limit headers: `X-RateLimit-*`

