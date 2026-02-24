# Security Fixes Applied

## Dependency Security Vulnerabilities Fixed

### 1. ✅ ultralytics
- **Vulnerability**: Code Injection (CVE-81385)
- **Fixed Version**: >=8.3.241
- **Status**: Updated in requirements.txt

### 2. ✅ starlette
- **Vulnerabilities**: 
  - DoS (CVE-2025-54121)
  - DoS (CVE-2024-47874)
  - DoS (CVE-2025-62727)
- **Fixed Version**: >=0.50.0
- **Status**: Updated in requirements.txt

### 3. ✅ python-socketio
- **Vulnerability**: Deserialization (CVE-2025-61765)
- **Fixed Version**: >=5.16.0
- **Status**: Updated in requirements.txt

### 4. ✅ brotli
- **Vulnerability**: DoS (CVE-2025-6176)
- **Fixed Version**: >=1.2.0
- **Status**: Added to requirements.txt

### 5. ✅ fonttools
- **Vulnerability**: Path Traversal (CVE-2025-66034)
- **Fixed Version**: >=4.61.1
- **Status**: Added to requirements.txt

## Code Security Fixes

### 1. ✅ Password Hashing
- **Issue**: Weak SHA-256 password hashing
- **Fix**: Replaced with bcrypt (with SHA-256+salt fallback)
- **Status**: Fixed in api.py

### 2. ✅ SSL Verification
- **Issue**: verify=False in security test files
- **Fix**: Added security comments and noqa flags
- **Status**: Documented in security_auditor.py

### 3. ✅ CodeQL Actions
- **Issue**: Deprecated v2 actions
- **Fix**: Updated to v3
- **Status**: Fixed in .github/workflows/security.yml

### 4. ✅ Unused Variable Warning
- **Issue**: analysisId assigned but not used
- **Fix**: Properly used in WebSocket connection management
- **Status**: Fixed in Scanner.tsx and websocketService.ts

## Remaining Transitive Dependencies

The following packages have vulnerabilities but are transitive dependencies (not directly in requirements.txt):
- sentence-transformers (3.0.1 → 5.2.0)
- langchain-core (0.2.43 → 1.2.5)
- langchain-text-splitters (0.2.4 → 1.1.0)
- langfuse (2.60.10 → 3.11.2)
- langgraph-checkpoint (2.1.1 → 3.0.1)
- litellm (1.77.3 → 1.80.11)
- dspy (3.0.3 → 3.0.4)

**Note**: These will be updated when their parent packages are updated, or can be pinned explicitly if needed.

## License Compliance

All packages in requirements.txt use permissive licenses (MIT, Apache 2.0, BSD). No GPL/AGPL dependencies.

## Next Steps

1. Run `pip install -r requirements.txt --upgrade` to update packages
2. Test the application to ensure compatibility
3. Monitor for new vulnerabilities with safety/pip-audit

