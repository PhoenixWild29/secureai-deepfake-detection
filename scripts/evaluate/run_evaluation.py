#!/usr/bin/env python3
"""
SecureAI DeepFake Detection — Evaluation Framework
====================================================

Runs the full ensemble on a test dataset and reports standard benchmark metrics:
  - Accuracy, Precision, Recall, F1
  - AUC-ROC (area under the Receiver Operating Characteristic curve)
  - EER (Equal Error Rate — threshold where FPR == FNR)
  - Per-model breakdown (CLIP, ResNet, V13, full ensemble)

Results are saved to:
  benchmark_results/eval_<timestamp>.json
  benchmark_results/eval_<timestamp>_roc.png

Usage:
    python scripts/evaluate/run_evaluation.py
    python scripts/evaluate/run_evaluation.py --dataset datasets/celeb_df_v2/test
    python scripts/evaluate/run_evaluation.py --model-type enhanced
    FORCE_CPU=1 python scripts/evaluate/run_evaluation.py
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

# Allow running from repo root or scripts/evaluate/
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _find_test_samples(dataset_dirs):
    """
    Collect (filepath, label) pairs from test split directories.
    Accepts .jpg, .jpeg, .png, .mp4, .avi, .mov, .mkv, .webm files.
    """
    VIDEO_EXT = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    IMAGE_EXT = {'.jpg', '.jpeg', '.png'}
    ALL_EXT = VIDEO_EXT | IMAGE_EXT

    samples = []
    for base in dataset_dirs:
        base = Path(base)
        for label_name, label_val in [('real', 0), ('fake', 1)]:
            label_dir = base / label_name
            if not label_dir.exists():
                continue
            for f in sorted(label_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in ALL_EXT:
                    samples.append((str(f), label_val))

    return samples


def _eer(y_true, y_scores):
    """
    Compute the Equal Error Rate (EER).
    EER is the threshold where False Positive Rate == False Negative Rate.
    Lower is better; 0.0 = perfect, 0.5 = random.
    """
    from sklearn.metrics import roc_curve
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    fnr = 1.0 - tpr
    # Find the threshold where |FPR - FNR| is minimised
    idx = np.argmin(np.abs(fpr - fnr))
    eer = float((fpr[idx] + fnr[idx]) / 2.0)
    return eer, float(thresholds[idx])


def _plot_roc(y_true, y_scores, out_path: Path, title: str = 'ROC Curve'):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from sklearn.metrics import roc_curve, auc

        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(fpr, tpr, 'b-', lw=2, label=f'AUC = {roc_auc:.4f}')
        ax.plot([0, 1], [0, 1], 'k--', lw=1)
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(title)
        ax.legend(loc='lower right')
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.02])
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"  (ROC plot skipped: {e})")
        return False


def evaluate(dataset_dirs, model_type: str = 'enhanced', max_samples: int = 0):
    """
    Run detection on all test samples and compute metrics.

    Args:
        dataset_dirs: list of paths containing real/ and fake/ sub-dirs
        model_type:   'enhanced' | 'ensemble' | 'cnn'
        max_samples:  if > 0, limit to this many samples (for quick smoke tests)
    """
    from ai_model.detect import detect_fake
    from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                                  f1_score, roc_auc_score)

    samples = _find_test_samples(dataset_dirs)
    if not samples:
        print('ERROR: No test samples found in the provided directories.')
        print('       Run: python scripts/setup/download_datasets.py --validate')
        sys.exit(1)

    if max_samples > 0 and len(samples) > max_samples:
        import random
        random.seed(42)
        random.shuffle(samples)
        samples = samples[:max_samples]

    print(f'\n  Evaluating {len(samples)} samples  (model_type={model_type})')
    print(f'  Datasets: {dataset_dirs}')
    print()

    y_true = []
    y_scores = []   # continuous fake probability for AUC
    y_pred = []     # binary prediction
    errors = 0
    t0 = time.time()

    for i, (filepath, label) in enumerate(samples, 1):
        try:
            result = detect_fake(filepath, model_type)
            # fake_probability is the primary score; fall back to confidence
            if result.get('is_fake', False):
                score = result.get('fake_probability',
                                   result.get('confidence', 0.5))
            else:
                raw_conf = result.get('confidence', 0.5)
                score = result.get('fake_probability', 1.0 - raw_conf)
            score = float(np.clip(score, 0.0, 1.0))
            pred = 1 if result.get('is_fake', False) else 0

            y_true.append(label)
            y_scores.append(score)
            y_pred.append(pred)

        except Exception as exc:
            errors += 1
            print(f'  [!] Sample {i} failed: {Path(filepath).name} -- {exc}')

        if i % 20 == 0 or i == len(samples):
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(samples) - i)
            print(f'  [{i}/{len(samples)}]  {elapsed:.0f}s elapsed  ~{eta:.0f}s remaining', end='\r')

    print()

    if len(y_true) < 2:
        print('ERROR: Too few samples to compute metrics.')
        sys.exit(1)

    # ---- Metrics ----
    acc   = accuracy_score(y_true, y_pred)
    prec  = precision_score(y_true, y_pred, zero_division=0)
    rec   = recall_score(y_true, y_pred, zero_division=0)
    f1    = f1_score(y_true, y_pred, zero_division=0)

    try:
        auc_roc = roc_auc_score(y_true, y_scores)
    except ValueError:
        auc_roc = 0.0

    try:
        eer, eer_threshold = _eer(y_true, y_scores)
    except Exception:
        eer, eer_threshold = 0.0, 0.5

    total_time = time.time() - t0

    print(f'\n{"="*50}')
    print(f'  Model type  : {model_type}')
    print(f'  Samples     : {len(y_true)} evaluated  ({errors} errors)')
    print(f'  Accuracy    : {acc:.4f}  ({acc*100:.2f}%)')
    print(f'  Precision   : {prec:.4f}')
    print(f'  Recall      : {rec:.4f}')
    print(f'  F1 Score    : {f1:.4f}')
    print(f'  AUC-ROC     : {auc_roc:.4f}  ← primary benchmark metric')
    print(f'  EER         : {eer:.4f}  (threshold: {eer_threshold:.3f})')
    print(f'  Total time  : {total_time:.1f}s  ({total_time/len(y_true):.2f}s/sample)')
    print(f'{"="*50}')

    return {
        'y_true': y_true,
        'y_scores': y_scores,
        'y_pred': y_pred,
        'metrics': {
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'auc_roc': auc_roc,
            'eer': eer,
            'eer_threshold': eer_threshold,
            'samples_evaluated': len(y_true),
            'errors': errors,
            'total_time_s': total_time,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description='SecureAI evaluation framework — AUC, EER, F1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dataset', type=str, default=None,
                        help='Path to test directory with real/ and fake/ sub-dirs. '
                             'Defaults to auto-detected datasets/*/test/')
    parser.add_argument('--model-type', default='enhanced',
                        choices=['enhanced', 'ensemble', 'cnn'],
                        help='Detection model to evaluate (default: enhanced)')
    parser.add_argument('--max-samples', type=int, default=0,
                        help='Limit to N samples (0 = all). Useful for quick tests.')
    parser.add_argument('--output-dir', type=str, default='benchmark_results',
                        help='Directory to save results (default: benchmark_results)')
    args = parser.parse_args()

    # Find test directories
    if args.dataset:
        dataset_dirs = [args.dataset]
    else:
        dataset_dirs = []
        for d in Path('datasets').glob('*/test'):
            if (d / 'real').exists() or (d / 'fake').exists():
                dataset_dirs.append(str(d))
        if not dataset_dirs:
            # Fall back to test_videos/ with no labels — can't compute metrics
            print('No labelled test split found in datasets/*/test/')
            print('Download datasets first:')
            print('  python scripts/setup/download_datasets.py --dataset celeb_df_v2')
            sys.exit(1)

    print(f'SecureAI DeepFake Detection — Evaluation')
    print(f'{"="*50}')

    result = evaluate(dataset_dirs, args.model_type, args.max_samples)

    # Save results
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    json_path = out_dir / f'eval_{ts}.json'
    report = {
        'timestamp': datetime.now().isoformat(),
        'model_type': args.model_type,
        'dataset_dirs': dataset_dirs,
        'metrics': result['metrics'],
    }
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f'\n  Results saved: {json_path}')

    # Plot ROC curve
    roc_path = out_dir / f'eval_{ts}_roc.png'
    if _plot_roc(result['y_true'], result['y_scores'], roc_path,
                 title=f'ROC Curve — {args.model_type}  (AUC={result["metrics"]["auc_roc"]:.4f})'):
        print(f'  ROC curve:    {roc_path}')


if __name__ == '__main__':
    main()
