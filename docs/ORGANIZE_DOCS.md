# Documentation Organization Plan

## Folder Structure Created

### Active Documentation (`docs/`)
- **deployment/** - Current deployment guides
- **setup/** - Current setup guides  
- **v13/** - V13 model documentation (current)
- **troubleshooting/** - Current troubleshooting guides
- **models/** - Model-related documentation
- **infrastructure/** - Infrastructure setup (S3, Redis, PostgreSQL, etc.)

### Archived Documentation (`archive/`)
- **v13/** - Old V13 troubleshooting (now that it's working)
- **laa-net/** - LAA-Net related (decided not to use)
- **cuda/** - CUDA fixes (completed)
- **old-setup/** - Superseded setup guides

### Scripts (`scripts/`)
- **test/** - Test scripts
- **diagnostic/** - Diagnostic/check scripts
- **deployment/** - Deployment scripts

## Files to Move

### Current V13 Docs (Keep Active)
- V13_SUCCESS_SUMMARY.md → docs/v13/
- UPGRADE_DIGITALOCEAN_RAM.md → docs/v13/
- V13_ROOT_CAUSE_ANALYSIS.md → docs/v13/
- INSTALL_BEST_MODELS.md → docs/models/
- QUICK_START_BEST_MODELS.md → docs/models/
- BUILD_BEST_MODEL_PLAN.md → docs/models/
- ULTIMATE_MODEL_IMPLEMENTATION_PLAN.md → docs/models/

### Archive V13 Troubleshooting (Old)
- FIX_V13_*.md → archive/v13/
- DEBUG_V13_*.md → archive/v13/
- GET_V13_WORKING.md → archive/v13/
- V13_DOWNLOAD_*.md → archive/v13/
- V13_PROGRESS_UPDATE.md → archive/v13/
- TEST_V13_FIXED.md → archive/v13/
- FIX_BACKBONE_NAMES.md → archive/v13/
- FIX_VIT_LARGE_HANG_FINAL.md → archive/v13/

### Archive LAA-Net (Not Using)
- *LAANET*.md → archive/laa-net/
- DOWNLOAD_LAANET_*.md → archive/laa-net/
- FIND_LAANET_*.md → archive/laa-net/
- GET_LAANET_*.md → archive/laa-net/
- STEP_2_*.md → archive/laa-net/
- contact_laa_net_maintainers.md → archive/laa-net/

### Archive CUDA (Completed)
- CUDA_*.md → archive/cuda/
- FIX_CUDA_*.md → archive/cuda/
- APPLY_CUDA_FIX_*.md → archive/cuda/
- FINAL_CUDA_FIX.md → archive/cuda/
- SUPPRESS_CUDA_ERRORS.md → archive/cuda/

### Deployment Docs (Active)
- DEPLOYMENT*.md → docs/deployment/
- QUICK_DEPLOY*.md → docs/deployment/
- PRODUCTION_DEPLOYMENT_*.md → docs/deployment/
- DIGITALOCEAN_SETUP_GUIDE.md → docs/deployment/
- CREATE_CLOUD_SERVER.md → docs/deployment/
- POWER_OFF_DROPLET.md → docs/deployment/

### Setup Docs (Active)
- SETUP_*.md → docs/setup/
- QUICK_SETUP_*.md → docs/setup/
- STEP_BY_STEP_*.md → docs/setup/
- GET_STARTED_*.md → docs/setup/
- START_HERE.md → docs/setup/

### Infrastructure Docs (Active)
- S3_*.md → docs/infrastructure/
- REDIS_*.md → docs/infrastructure/
- POSTGRESQL_*.md → docs/infrastructure/
- HTTPS_SETUP_*.md → docs/infrastructure/
- SUBDOMAIN_SETUP_*.md → docs/infrastructure/
- DNS_SETUP_*.md → docs/infrastructure/

### Test Scripts
- test_*.py → scripts/test/
- check_*.py → scripts/diagnostic/
- diagnose_*.py → scripts/diagnostic/
- fix_*.py → scripts/diagnostic/
- *.sh → scripts/deployment/ (if deployment related)
