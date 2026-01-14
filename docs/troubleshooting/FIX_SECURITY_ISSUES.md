# Security Issues Fix Plan

## Issues to Fix

### 1. Dependency Security Vulnerabilities
- **Action**: Update all packages to latest secure versions
- **Method**: Run `safety check` and `pip-audit` to identify vulnerabilities, then update packages

### 2. License Compliance
- **Action**: Ensure all dependencies have compatible licenses
- **Method**: Use `pip-licenses` to check and document all licenses

### 3. CodeQL High Severity Issues
- **Action**: Fix actual security vulnerabilities in code
- **Issues to address**:
  - Weak password hashing (SHA-256) → Fixed with bcrypt
  - Unused variables → Fixed by proper usage
  - Potential SQL injection → Using SQLAlchemy ORM (parameterized queries)
  - SSL verification disabled → Need to check and fix

### 4. CodeQL Actions Deprecation
- **Action**: Update from v2 to v3
- **Status**: ✅ Updated

## Next Steps

1. Update packages based on safety/pip-audit results
2. Fix any remaining CodeQL alerts
3. Ensure license compliance
4. Test all fixes

