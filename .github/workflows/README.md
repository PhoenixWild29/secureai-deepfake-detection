# GitHub Actions Workflows

## 🚀 CI/CD Pipeline Overview

This directory contains GitHub Actions workflows for automated testing, security scanning, deployment, and release management.

---

## 📋 Available Workflows

### **1. Continuous Integration (`ci.yml`)** ✅ Always Running

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main`, `master`, or `develop`

**What It Does:**
- ✅ Code quality checks (Black, isort, flake8, mypy, pylint)
- ✅ Security scanning (Bandit, Safety)
- ✅ Python unit tests (Python 3.9, 3.10, 3.11)
- ✅ Frontend tests and build
- ✅ Integration tests (with PostgreSQL and Redis)
- ✅ Code coverage reporting

**Duration:** ~10-15 minutes

**Status Badge:**
```markdown
![CI](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Continuous%20Integration/badge.svg)
```

---

### **2. Security Scanning (`security.yml`)** 🔒 Weekly + On Demand

**Triggers:**
- Push to `main`, `master`, or `develop`
- Pull requests to `main` or `master`
- Weekly schedule (Monday 2 AM UTC)

**What It Does:**
- ✅ Dependency vulnerability scanning (Safety, pip-audit)
- ✅ Code security analysis (Bandit)
- ✅ Container security scanning (Trivy)
- ✅ Secrets detection (Gitleaks, TruffleHog)
- ✅ License compliance checking
- ✅ CodeQL security analysis

**Duration:** ~15-20 minutes

**Status Badge:**
```markdown
![Security](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Security%20Scanning/badge.svg)
```

---

### **3. Deployment (`deploy.yml`)** 🚀 Production Deployment

**Triggers:**
- Push to `master` or `main` branch
- Tags matching `v*`
- Manual workflow dispatch

**What It Does:**
- ✅ Pre-deployment validation checks
- ✅ Build Docker images
- ✅ Deploy to staging (from `develop`)
- ✅ Deploy to production (from `master`/`main`)
- ✅ Post-deployment validation
- ✅ Health checks and smoke tests

**Duration:** ~20-30 minutes

**Environments:**
- Staging: `staging.secureai.com`
- Production: `secureai.com`

**Manual Deployment:**
Go to Actions → Deploy to Production → Run workflow

---

### **4. Release Automation (`release.yml`)** 📦 Automated Releases

**Triggers:**
- Push tags matching `v*.*.*` (semantic versioning)

**What It Does:**
- ✅ Generate changelog from commits
- ✅ Create release notes
- ✅ Build release assets (tarball, zip)
- ✅ Create GitHub release
- ✅ Publish release packages
- ✅ Notify stakeholders

**Usage:**
```bash
# Create and push a release tag
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
```

**Duration:** ~10 minutes

---

### **5. Performance Testing (`performance-tests.yml`)** ⚡ Weekly Performance Checks

**Triggers:**
- Weekly schedule (Sunday 3 AM UTC)
- Manual workflow dispatch

**What It Does:**
- ✅ Performance validation tests
- ✅ Load testing (50-100 concurrent users)
- ✅ Benchmark tests
- ✅ Performance metrics collection
- ✅ Regression detection

**Test Types:**
- Standard: Regular performance testing
- Load: 50 users, 180s duration
- Stress: 100 users, 300s duration
- Endurance: Long-running tests

**Duration:** ~30-60 minutes

---

### **6. Compliance Checks (`compliance.yml`)** 📋 Monthly Compliance

**Triggers:**
- Monthly schedule (1st of month, 9 AM UTC)
- Manual workflow dispatch
- Changes to compliance files

**What It Does:**
- ✅ GDPR compliance assessment
- ✅ CCPA compliance assessment
- ✅ AI Act compliance assessment
- ✅ Comprehensive compliance report
- ✅ Compliance findings documentation
- ✅ Auto-create issues for compliance gaps

**Duration:** ~15-20 minutes

---

### **7. Documentation Build (`documentation.yml`)** 📚 Docs Automation

**Triggers:**
- Push to `main` or `master` with markdown changes
- Manual workflow dispatch

**What It Does:**
- ✅ Validate markdown links
- ✅ Lint markdown files
- ✅ Check documentation completeness
- ✅ Build documentation website (MkDocs)
- ✅ Deploy to GitHub Pages

**Documentation Site:** https://phoenixwild29.github.io/secureai-deepfake-detection/

**Duration:** ~5-10 minutes

---

### **8. Docker Build (`docker-build.yml`)** 🐳 Container Management

**Triggers:**
- Push to `main`, `master`, or `develop`
- Pull requests
- Tags

**What It Does:**
- ✅ Build Docker images
- ✅ Push to GitHub Container Registry
- ✅ Tag with version/branch/sha
- ✅ Test container health
- ✅ Scan for vulnerabilities

**Container Registry:** `ghcr.io/phoenixwild29/secureai-deepfake-detection`

**Duration:** ~10-15 minutes

---

## 🔧 Workflow Configuration

### **Required Secrets**

Configure these secrets in: Repository Settings → Secrets and variables → Actions

```yaml
# Deployment Secrets (Optional)
PROD_HOST: Production server hostname
PROD_USER: SSH username for deployment
PROD_SSH_KEY: SSH private key for deployment
AWS_ACCESS_KEY_ID: AWS access key (if using AWS)
AWS_SECRET_ACCESS_KEY: AWS secret key (if using AWS)

# Notification Secrets (Optional)
SLACK_WEBHOOK: Slack webhook URL for notifications
DISCORD_WEBHOOK: Discord webhook URL

# Service Secrets (Optional)
CODECOV_TOKEN: Codecov token for coverage reports
```

### **Required Variables**

Configure in: Repository Settings → Secrets and variables → Actions → Variables

```yaml
PYTHON_VERSION: '3.11'
NODE_VERSION: '18'
STAGING_URL: 'https://staging.secureai.com'
PRODUCTION_URL: 'https://secureai.com'
```

---

## 🎯 Workflow Status Badges

Add these to your README.md:

```markdown
## Build Status

![CI](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Continuous%20Integration/badge.svg)
![Security](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Security%20Scanning/badge.svg)
![Deploy](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Deploy%20to%20Production/badge.svg)
![Docker](https://github.com/PhoenixWild29/secureai-deepfake-detection/workflows/Docker%20Build%20%26%20Publish/badge.svg)
```

---

## 📊 Workflow Schedule Summary

| Workflow | Schedule | Duration | Purpose |
|----------|----------|----------|---------|
| CI | On every push/PR | 10-15 min | Code quality and testing |
| Security | Weekly (Mon 2 AM) | 15-20 min | Security vulnerability scanning |
| Performance | Weekly (Sun 3 AM) | 30-60 min | Performance regression testing |
| Compliance | Monthly (1st, 9 AM) | 15-20 min | Regulatory compliance checks |
| Documentation | On doc changes | 5-10 min | Build and deploy docs |
| Docker | On push | 10-15 min | Build container images |
| Deploy | On master push | 20-30 min | Deploy to production |
| Release | On version tag | 10 min | Create GitHub releases |

---

## 🚀 Quick Actions

### **Manual Workflow Triggers**

All workflows can be manually triggered:

1. Go to: Actions tab in GitHub
2. Select the workflow
3. Click "Run workflow"
4. Choose branch and options
5. Click "Run workflow" button

### **Deploy to Production**
```
Actions → Deploy to Production → Run workflow
- Branch: master
- Environment: production
→ Run workflow
```

### **Run Security Scan**
```
Actions → Security Scanning → Run workflow
- Branch: master
→ Run workflow
```

### **Run Performance Tests**
```
Actions → Performance & Load Testing → Run workflow
- Branch: master
- Test type: standard/load/stress
→ Run workflow
```

---

## 🔧 Customization Guide

### **To Enable Production Deployment**

Edit `.github/workflows/deploy.yml`:

```yaml
- name: Deploy to production
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.PROD_HOST }}
    username: ${{ secrets.PROD_USER }}
    key: ${{ secrets.PROD_SSH_KEY }}
    script: |
      cd /opt/secureai-deepfake-detection
      git pull origin master
      source .venv/bin/activate
      pip install -r requirements.txt
      sudo systemctl restart secureai
```

### **To Add Slack Notifications**

Add to any workflow:

```yaml
- name: Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    channel: '#deployments'
    text: |
      Workflow: ${{ github.workflow }}
      Status: ${{ job.status }}
      Commit: ${{ github.sha }}
      Author: ${{ github.actor }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

---

## 📚 Additional Resources

### **GitHub Actions Documentation**
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Security Hardening](https://docs.github.com/en/actions/security-guides)

### **Useful Actions**
- [checkout](https://github.com/actions/checkout)
- [setup-python](https://github.com/actions/setup-python)
- [upload-artifact](https://github.com/actions/upload-artifact)
- [docker/build-push-action](https://github.com/docker/build-push-action)

---

## ✅ Workflow Checklist

Before pushing to production:

- [ ] All CI tests passing
- [ ] Security scans clean
- [ ] Performance tests passing
- [ ] Compliance assessments green
- [ ] Docker images building successfully
- [ ] Documentation up to date
- [ ] Staging deployment successful
- [ ] Production secrets configured
- [ ] Deployment script tested
- [ ] Rollback plan ready

---

**🎉 Your CI/CD Pipeline is Ready!**

All workflows are configured and will run automatically based on their triggers.

*For questions or issues with workflows, contact DevOps team or check GitHub Actions documentation.*
