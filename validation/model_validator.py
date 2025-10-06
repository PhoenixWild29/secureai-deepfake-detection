#!/usr/bin/env python3
"""
Model Validation Logic
Comprehensive model validation, performance testing, and quality assurance
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelValidator:
    """
    Comprehensive model validation and performance testing.
    """
    
    def __init__(
        self,
        validation_threshold: float = 0.95,
        test_size: float = 0.2,
        random_state: int = 42
    ):
        """
        Initialize model validator.
        
        Args:
            validation_threshold: AUC threshold for validation
            test_size: Test data split ratio
            random_state: Random state for reproducibility
        """
        self.validation_threshold = validation_threshold
        self.test_size = test_size
        self.random_state = random_state
        
        logger.info(f"Model validator initialized with threshold: {validation_threshold}")
    
    def validate_model_performance(
        self,
        model,
        test_data: pd.DataFrame,
        feature_columns: List[str],
        label_column: str,
        model_type: str = "ensemble"
    ) -> Dict[str, Any]:
        """
        Validate model performance on test data.
        
        Args:
            model: Trained model
            test_data: Test dataset
            feature_columns: Feature column names
            label_column: Label column name
            model_type: Type of model being validated
            
        Returns:
            Validation results dictionary
        """
        try:
            logger.info(f"Validating {model_type} model performance")
            
            # Prepare test data
            X_test = test_data[feature_columns].values
            y_test = test_data[label_column].values
            
            # Get predictions
            if model_type == "ensemble":
                predictions, probabilities = self._get_ensemble_predictions(model, X_test)
            else:
                predictions, probabilities = self._get_sklearn_predictions(model, X_test)
            
            # Calculate metrics
            metrics = self._calculate_metrics(y_test, predictions, probabilities)
            
            # Validate against threshold
            auc_score = metrics['auc_score']
            is_valid = auc_score >= self.validation_threshold
            
            # Generate detailed analysis
            analysis = self._generate_performance_analysis(y_test, predictions, probabilities)
            
            validation_results = {
                'is_valid': is_valid,
                'auc_score': auc_score,
                'validation_threshold': self.validation_threshold,
                'metrics': metrics,
                'analysis': analysis,
                'validation_timestamp': datetime.now(timezone.utc).isoformat(),
                'test_samples': len(y_test),
                'model_type': model_type
            }
            
            logger.info(f"Model validation completed: {'Valid' if is_valid else 'Invalid'} (AUC: {auc_score:.4f})")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating model performance: {str(e)}")
            raise
    
    def _get_ensemble_predictions(self, model, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get predictions from ensemble model.
        
        Args:
            model: Ensemble model
            X_test: Test features
            
        Returns:
            Tuple of (predictions, probabilities)
        """
        model.eval()
        
        with torch.no_grad():
            # Convert to tensor
            X_tensor = torch.FloatTensor(X_test)
            
            # Get model output
            outputs = model(X_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            predictions = torch.argmax(outputs, dim=1)
            
            return predictions.numpy(), probabilities[:, 1].numpy()  # Probability of positive class
    
    def _get_sklearn_predictions(self, model, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get predictions from sklearn model.
        
        Args:
            model: Sklearn model
            X_test: Test features
            
        Returns:
            Tuple of (predictions, probabilities)
        """
        predictions = model.predict(X_test)
        
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X_test)[:, 1]  # Probability of positive class
        else:
            probabilities = predictions  # Fallback for models without probability prediction
        
        return predictions, probabilities
    
    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_prob: Prediction probabilities
            
        Returns:
            Metrics dictionary
        """
        try:
            # Basic classification metrics
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            # AUC score
            try:
                auc_score = roc_auc_score(y_true, y_prob)
            except ValueError:
                # Handle case where only one class is present
                auc_score = 0.5
            
            # Per-class metrics
            precision_per_class = precision_score(y_true, y_pred, average=None, zero_division=0)
            recall_per_class = recall_score(y_true, y_pred, average=None, zero_division=0)
            f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
            
            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            
            metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'auc_score': auc_score,
                'precision_per_class': precision_per_class.tolist(),
                'recall_per_class': recall_per_class.tolist(),
                'f1_per_class': f1_per_class.tolist(),
                'confusion_matrix': cm.tolist(),
                'true_positives': int(cm[1, 1]) if cm.shape == (2, 2) else 0,
                'true_negatives': int(cm[0, 0]) if cm.shape == (2, 2) else 0,
                'false_positives': int(cm[0, 1]) if cm.shape == (2, 2) else 0,
                'false_negatives': int(cm[1, 0]) if cm.shape == (2, 2) else 0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'auc_score': 0.0,
                'error': str(e)
            }
    
    def _generate_performance_analysis(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray
    ) -> Dict[str, Any]:
        """
        Generate detailed performance analysis.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_prob: Prediction probabilities
            
        Returns:
            Analysis dictionary
        """
        try:
            # Class distribution
            unique_classes, class_counts = np.unique(y_true, return_counts=True)
            class_distribution = dict(zip(unique_classes.tolist(), class_counts.tolist()))
            
            # Prediction confidence analysis
            confidence_stats = {
                'mean_confidence': float(np.mean(y_prob)),
                'std_confidence': float(np.std(y_prob)),
                'min_confidence': float(np.min(y_prob)),
                'max_confidence': float(np.max(y_prob)),
                'median_confidence': float(np.median(y_prob))
            }
            
            # Error analysis
            errors = y_pred != y_true
            error_rate = float(np.mean(errors))
            
            # High confidence errors
            high_conf_errors = errors & (y_prob > 0.8)
            high_conf_error_rate = float(np.mean(high_conf_errors))
            
            # Low confidence predictions
            low_conf_predictions = y_prob < 0.3
            low_conf_rate = float(np.mean(low_conf_predictions))
            
            analysis = {
                'class_distribution': class_distribution,
                'confidence_stats': confidence_stats,
                'error_rate': error_rate,
                'high_confidence_error_rate': high_conf_error_rate,
                'low_confidence_rate': low_conf_rate,
                'total_samples': len(y_true),
                'error_samples': int(np.sum(errors)),
                'high_conf_error_samples': int(np.sum(high_conf_errors)),
                'low_conf_samples': int(np.sum(low_conf_predictions))
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating performance analysis: {str(e)}")
            return {'error': str(e)}
    
    def validate_model_robustness(
        self,
        model,
        test_data: pd.DataFrame,
        feature_columns: List[str],
        label_column: str,
        noise_levels: List[float] = [0.01, 0.05, 0.1],
        model_type: str = "ensemble"
    ) -> Dict[str, Any]:
        """
        Validate model robustness to noise.
        
        Args:
            model: Trained model
            test_data: Test dataset
            feature_columns: Feature column names
            label_column: Label column name
            noise_levels: Noise levels to test
            model_type: Type of model
            
        Returns:
            Robustness validation results
        """
        try:
            logger.info(f"Validating model robustness with noise levels: {noise_levels}")
            
            X_test = test_data[feature_columns].values
            y_test = test_data[label_column].values
            
            # Baseline performance
            baseline_results = self.validate_model_performance(
                model, test_data, feature_columns, label_column, model_type
            )
            
            robustness_results = {
                'baseline': baseline_results,
                'noise_tests': {},
                'robustness_score': 0.0
            }
            
            # Test with different noise levels
            for noise_level in noise_levels:
                logger.info(f"Testing robustness with {noise_level} noise")
                
                # Add noise to test data
                noise = np.random.normal(0, noise_level, X_test.shape)
                X_noisy = X_test + noise
                
                # Create noisy test data
                noisy_test_data = test_data.copy()
                noisy_test_data[feature_columns] = X_noisy
                
                # Validate performance on noisy data
                noisy_results = self.validate_model_performance(
                    model, noisy_test_data, feature_columns, label_column, model_type
                )
                
                robustness_results['noise_tests'][str(noise_level)] = noisy_results
            
            # Calculate robustness score
            baseline_auc = baseline_results['auc_score']
            noise_performance_drops = []
            
            for noise_level, results in robustness_results['noise_tests'].items():
                noise_auc = results['auc_score']
                performance_drop = baseline_auc - noise_auc
                noise_performance_drops.append(performance_drop)
            
            # Robustness score: lower performance drop = higher robustness
            avg_performance_drop = np.mean(noise_performance_drops)
            robustness_score = max(0, 1 - avg_performance_drop)
            robustness_results['robustness_score'] = robustness_score
            
            logger.info(f"Model robustness validation completed. Score: {robustness_score:.4f}")
            return robustness_results
            
        except Exception as e:
            logger.error(f"Error validating model robustness: {str(e)}")
            raise
    
    def validate_model_fairness(
        self,
        model,
        test_data: pd.DataFrame,
        feature_columns: List[str],
        label_column: str,
        sensitive_attributes: List[str],
        model_type: str = "ensemble"
    ) -> Dict[str, Any]:
        """
        Validate model fairness across sensitive attributes.
        
        Args:
            model: Trained model
            test_data: Test dataset
            feature_columns: Feature column names
            label_column: Label column name
            sensitive_attributes: Sensitive attribute columns
            model_type: Type of model
            
        Returns:
            Fairness validation results
        """
        try:
            logger.info(f"Validating model fairness for attributes: {sensitive_attributes}")
            
            fairness_results = {
                'overall_performance': {},
                'group_performance': {},
                'fairness_metrics': {}
            }
            
            # Overall performance
            overall_results = self.validate_model_performance(
                model, test_data, feature_columns, label_column, model_type
            )
            fairness_results['overall_performance'] = overall_results
            
            # Group-wise performance
            for attr in sensitive_attributes:
                if attr not in test_data.columns:
                    logger.warning(f"Sensitive attribute {attr} not found in test data")
                    continue
                
                attr_results = {}
                unique_values = test_data[attr].unique()
                
                for value in unique_values:
                    group_data = test_data[test_data[attr] == value]
                    
                    if len(group_data) < 10:  # Skip groups with too few samples
                        logger.warning(f"Skipping group {attr}={value} (only {len(group_data)} samples)")
                        continue
                    
                    group_results = self.validate_model_performance(
                        model, group_data, feature_columns, label_column, model_type
                    )
                    attr_results[str(value)] = group_results
                
                fairness_results['group_performance'][attr] = attr_results
            
            # Calculate fairness metrics
            fairness_metrics = self._calculate_fairness_metrics(fairness_results)
            fairness_results['fairness_metrics'] = fairness_metrics
            
            logger.info("Model fairness validation completed")
            return fairness_results
            
        except Exception as e:
            logger.error(f"Error validating model fairness: {str(e)}")
            raise
    
    def _calculate_fairness_metrics(self, fairness_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate fairness metrics from group performance results.
        
        Args:
            fairness_results: Fairness validation results
            
        Returns:
            Fairness metrics dictionary
        """
        try:
            fairness_metrics = {}
            
            for attr, group_results in fairness_results['group_performance'].items():
                if not group_results:
                    continue
                
                # Extract AUC scores for each group
                auc_scores = []
                for group_name, results in group_results.items():
                    if 'auc_score' in results:
                        auc_scores.append(results['auc_score'])
                
                if len(auc_scores) < 2:
                    continue
                
                # Calculate fairness metrics
                max_auc = max(auc_scores)
                min_auc = min(auc_scores)
                mean_auc = np.mean(auc_scores)
                
                # Demographic parity difference
                dpd = max_auc - min_auc
                
                # Equalized odds difference (simplified)
                eod = dpd  # Simplified version
                
                fairness_metrics[attr] = {
                    'demographic_parity_difference': dpd,
                    'equalized_odds_difference': eod,
                    'max_auc': max_auc,
                    'min_auc': min_auc,
                    'mean_auc': mean_auc,
                    'auc_range': max_auc - min_auc
                }
            
            return fairness_metrics
            
        except Exception as e:
            logger.error(f"Error calculating fairness metrics: {str(e)}")
            return {}
    
    def generate_validation_report(
        self,
        validation_results: Dict[str, Any],
        model_name: str,
        model_version: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive validation report.
        
        Args:
            validation_results: Validation results
            model_name: Model name
            model_version: Model version
            output_path: Output file path
            
        Returns:
            Report file path
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"validation_report_{model_name}_{model_version}_{timestamp}.html"
            
            # Generate HTML report
            html_content = self._generate_html_report(
                validation_results, model_name, model_version
            )
            
            # Save report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Validation report generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating validation report: {str(e)}")
            raise
    
    def _generate_html_report(
        self,
        validation_results: Dict[str, Any],
        model_name: str,
        model_version: str
    ) -> str:
        """
        Generate HTML validation report.
        
        Args:
            validation_results: Validation results
            model_name: Model name
            model_version: Model version
            
        Returns:
            HTML content
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Model Validation Report - {model_name} v{model_version}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
                .valid {{ color: green; font-weight: bold; }}
                .invalid {{ color: red; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Model Validation Report</h1>
                <h2>{model_name} Version {model_version}</h2>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h3>Validation Summary</h3>
                <p>Status: <span class="{'valid' if validation_results.get('is_valid', False) else 'invalid'}">
                    {'VALID' if validation_results.get('is_valid', False) else 'INVALID'}
                </span></p>
                <p>AUC Score: {validation_results.get('auc_score', 0):.4f}</p>
                <p>Validation Threshold: {validation_results.get('validation_threshold', 0):.4f}</p>
            </div>
            
            <div class="section">
                <h3>Performance Metrics</h3>
                <div class="metric">Accuracy: {validation_results.get('metrics', {}).get('accuracy', 0):.4f}</div>
                <div class="metric">Precision: {validation_results.get('metrics', {}).get('precision', 0):.4f}</div>
                <div class="metric">Recall: {validation_results.get('metrics', {}).get('recall', 0):.4f}</div>
                <div class="metric">F1 Score: {validation_results.get('metrics', {}).get('f1_score', 0):.4f}</div>
            </div>
            
            <div class="section">
                <h3>Confusion Matrix</h3>
                <table>
                    <tr><th></th><th>Predicted Negative</th><th>Predicted Positive</th></tr>
                    <tr><th>Actual Negative</th><td>{validation_results.get('metrics', {}).get('true_negatives', 0)}</td><td>{validation_results.get('metrics', {}).get('false_positives', 0)}</td></tr>
                    <tr><th>Actual Positive</th><td>{validation_results.get('metrics', {}).get('false_negatives', 0)}</td><td>{validation_results.get('metrics', {}).get('true_positives', 0)}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h3>Performance Analysis</h3>
                <p>Test Samples: {validation_results.get('test_samples', 0)}</p>
                <p>Error Rate: {validation_results.get('analysis', {}).get('error_rate', 0):.4f}</p>
                <p>Mean Confidence: {validation_results.get('analysis', {}).get('confidence_stats', {}).get('mean_confidence', 0):.4f}</p>
            </div>
        </body>
        </html>
        """
        
        return html


# Utility functions for easy access
def validate_model_performance(
    model,
    test_data: pd.DataFrame,
    feature_columns: List[str],
    label_column: str,
    validation_threshold: float = 0.95,
    model_type: str = "ensemble"
) -> Dict[str, Any]:
    """Validate model performance."""
    validator = ModelValidator(validation_threshold)
    return validator.validate_model_performance(
        model, test_data, feature_columns, label_column, model_type
    )


def validate_model_robustness(
    model,
    test_data: pd.DataFrame,
    feature_columns: List[str],
    label_column: str,
    validation_threshold: float = 0.95,
    model_type: str = "ensemble"
) -> Dict[str, Any]:
    """Validate model robustness."""
    validator = ModelValidator(validation_threshold)
    return validator.validate_model_robustness(
        model, test_data, feature_columns, label_column, model_type=model_type
    )


def generate_validation_report(
    validation_results: Dict[str, Any],
    model_name: str,
    model_version: str,
    output_path: Optional[str] = None
) -> str:
    """Generate validation report."""
    validator = ModelValidator()
    return validator.generate_validation_report(
        validation_results, model_name, model_version, output_path
    )


# Export
__all__ = [
    'ModelValidator',
    'validate_model_performance',
    'validate_model_robustness',
    'generate_validation_report'
]
