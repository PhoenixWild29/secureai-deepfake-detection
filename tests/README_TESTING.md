# DeepFake Detection Model - MLOps Test Suite

## Overview

Comprehensive automated testing infrastructure for validating the DeepFake Detection Model (DFDM) across functional, performance, robustness, bias, and explainability dimensions.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration and shared fixtures
├── test_data_loader.py           # Test dataset loading utilities
├── test_functional.py            # Functional and regression tests
├── test_performance.py           # Performance and latency benchmarks
├── test_adversarial.py           # Adversarial robustness tests
├── test_bias.py                  # Bias, fairness, and explainability tests
├── test_runner.py                # Main test execution runner
├── README_TESTING.md             # This file
└── test_data/                    # Test video datasets
    ├── real/
    │   ├── authentic_1080p/
    │   ├── authentic_720p/
    │   ├── authentic_360p/
    │   └── demographic_diverse/
    └── deepfake/
        ├── gan_based/
        │   ├── deepfacelab/
        │   └── faceswap/
        ├── diffusion_based/
        │   ├── stable_diffusion/
        │   └── runway_gen2/
        ├── compressed/
        │   └── compression_round_X/
        └── adversarial/
            └── pgd_attack/
```

## Quick Start

### Prerequisites

1. Ensure the DFDM API server is running:
   ```bash
   python api.py
   ```

2. Install test dependencies:
   ```bash
   pip install pytest requests pytest-xdist pytest-html
   ```

### Running Tests

#### Run All Tests
```bash
python tests/test_runner.py
```

#### Run Specific Category
```bash
# Functional tests only
python tests/test_runner.py --category functional

# Performance tests only
python tests/test_runner.py --category performance

# Adversarial robustness tests only
python tests/test_runner.py --category adversarial

# Bias/fairness tests only
python tests/test_runner.py --category bias
```

#### Quick CI/CD Tests
```bash
# Run only critical P0 tests
python tests/test_runner.py --quick
```

#### Verbose Output
```bash
# Detailed test output
python tests/test_runner.py --verbose
```

#### Using pytest Directly
```bash
# Run with pytest
pytest tests/ -v

# Run specific test file
pytest tests/test_functional.py -v

# Run with markers
pytest tests/ -m "functional" -v
pytest tests/ -m "performance or adversarial" -v

# Parallel execution (faster)
pytest tests/ -n auto
```

## Test Categories

### 1. Functional Tests (`test_functional.py`)

**Coverage:**
- Authentic video baseline (FPR validation)
- Deepfake detection rate (TPR validation)
- Multi-format video support
- Resolution scaling
- API stability
- Edge case handling

**Key Metrics:**
- False Positive Rate (FPR) < 2%
- True Positive Rate (TPR) > 95%
- Accuracy > 95%

### 2. Performance Tests (`test_performance.py`)

**Coverage:**
- Inference time per second
- Absolute latency benchmarks
- Concurrent processing
- Resolution-based latency

**Key Metrics:**
- Max 0.5s per second of video
- Absolute max 60 seconds
- 95% success rate under load

### 3. Adversarial Tests (`test_adversarial.py`)

**Coverage:**
- PGD attack robustness
- Compression resilience
- Diffusion model detection
- GAN variant detection
- Audio-visual mismatch
- Low-quality detection

**Key Metrics:**
- Adversarial robustness > 85%
- Compression resilience > 80%
- Diffusion detection > 85%

### 4. Bias Tests (`test_bias.py`)

**Coverage:**
- Demographic parity
- Equalized odds
- Saliency map generation
- Confidence calibration
- Forensic evidence quality

**Key Metrics:**
- Demographic CV < 0.15
- Saliency coverage > 80%
- ECE < 0.05

## Test Data Requirements

### Minimum Dataset Profile

- **Total Videos:** 5,000+
- **Authentic Videos:** 2,000+
- **Deepfake Videos:** 3,000+
- **Demographic Diversity:** 5+ groups
- **Quality Levels:** 360p, 720p, 1080p
- **Compression Rounds:** 5 levels

### Directory Structure

See `tests/test_data_loader.py` for expected directory structure.

## Test Reports

### Console Output

Test execution prints a human-readable summary:
```
================================================================================
TEST EXECUTION SUMMARY
================================================================================
Total Tests Run:    44
Tests Passed:       42
Tests Failed:       2
Tests Skipped:      0

Accuracy Metrics:
  Overall Accuracy:      96.5%
  Precision:             97.2%
  Recall (TPR):          95.8%
  F1 Score:              96.5%

Performance Metrics:
  Avg Latency per Sec:   0.34s
  P95 Latency:           0.89s
  Max Latency:           52.3s

================================================================================
```

### JSON Report

Detailed results saved to `test_results/test_report_TIMESTAMP.json`:

```json
{
  "metadata": {
    "timestamp": "2025-01-15T10:30:00",
    "test_suite_version": "1.0.0"
  },
  "summary": {
    "total_tests": 44,
    "passed": 42,
    "failed": 2
  },
  "accuracy_metrics": {
    "overall_accuracy": 0.965,
    "precision": 0.972,
    "recall": 0.958,
    "f1_score": 0.965
  },
  "misclassifications": {
    "false_positives": [
      {
        "filename": "sample_123.mp4",
        "confidence": 0.85,
        "category": "heavy_makeup"
      }
    ],
    "false_negatives": []
  }
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: DFDM Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-xdist
      - run: python api.py &
      - run: sleep 5  # Wait for server
      - run: python tests/test_runner.py --quick
      - uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

## Test Thresholds

Critical thresholds are defined in `conftest.py` and can be overridden:

```python
'test_thresholds' = {
    'max_fpr': 0.05,
    'min_recall': 0.90,
    'max_latency_per_second': 0.5,
    'adversarial_robustness_threshold': 0.85,
    'demographic_parity_cv': 0.15
}
```

## Troubleshooting

### API Not Accessible

```
Error: DFDM API is not accessible
```

**Solution:** Start the API server:
```bash
python api.py
```

### No Test Data Found

```
Error: No test data found in tests/test_data
```

**Solution:** Ensure test videos are organized in the expected directory structure.

### Import Errors

```bash
ModuleNotFoundError: No module named 'test_data_loader'
```

**Solution:** Run tests from project root:
```bash
cd SecureAI-DeepFake-Detection
python tests/test_runner.py
```

## Adding New Tests

1. Add test function to appropriate test file
2. Use appropriate pytest marker (`@pytest.mark.functional`, etc.)
3. Use shared fixtures from `conftest.py`
4. Follow existing test patterns

Example:
```python
@pytest.mark.functional
def test_new_feature(analysis_request, data_loader):
    """Test description"""
    # Test implementation
    assert condition, "Error message"
```

## Performance Tips

1. Use `pytest-xdist` for parallel execution
2. Run specific categories for faster feedback
3. Use `--quick` flag for CI/CD
4. Cache test datasets if regenerated frequently

## Contact

For issues or questions, contact the MLOps team.

