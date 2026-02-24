#!/usr/bin/env python3
"""
UAT Test Data Generator for SecureAI DeepFake Detection System
Generates realistic test data for User Acceptance Testing scenarios
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import random
import csv

class UATTestDataGenerator:
    """
    Generates comprehensive test data for UAT scenarios across all personas
    """
    
    def __init__(self, output_dir: str = "uat_test_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different data types
        self.video_dir = self.output_dir / "videos"
        self.metadata_dir = self.output_dir / "metadata"
        self.scenarios_dir = self.output_dir / "scenarios"
        self.reports_dir = self.output_dir / "reports"
        
        for dir_path in [self.video_dir, self.metadata_dir, self.scenarios_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def generate_security_professional_data(self) -> Dict[str, Any]:
        """Generate test data for security professional scenarios"""
        
        scenarios = {
            "executive_impersonation": {
                "name": "Executive Impersonation Campaign",
                "description": "Deepfake videos impersonating C-level executives",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "ceo_announcement_fake.mp4",
                        "technique": "face_swap",
                        "confidence_threshold": 0.95,
                        "urgency": "critical",
                        "metadata": {
                            "subject": "CEO financial announcement",
                            "suspected_actor": "unknown",
                            "threat_level": "high",
                            "timeline": "immediate_response_required"
                        }
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "cto_security_breach_fake.mp4",
                        "technique": "voice_cloning",
                        "confidence_threshold": 0.90,
                        "urgency": "high",
                        "metadata": {
                            "subject": "Security breach notification",
                            "suspected_actor": "external_threat",
                            "threat_level": "critical",
                            "timeline": "immediate_response_required"
                        }
                    }
                ]
            },
            "zero_day_attack": {
                "name": "Zero-Day Attack Simulation",
                "description": "Unknown deepfake techniques not in training data",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "novel_technique_001.mp4",
                        "technique": "unknown",
                        "confidence_threshold": 0.70,
                        "urgency": "medium",
                        "metadata": {
                            "novelty_score": 0.85,
                            "fallback_detection": True,
                            "manual_review_required": True
                        }
                    }
                ]
            },
            "multi_vector_campaign": {
                "name": "Multi-Vector Deepfake Campaign",
                "description": "Coordinated attack using multiple techniques",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "campaign_face_swap_001.mp4",
                        "technique": "face_swap",
                        "confidence_threshold": 0.92,
                        "campaign_id": "campaign_alpha_001"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "campaign_voice_clone_001.mp4",
                        "technique": "voice_cloning",
                        "confidence_threshold": 0.88,
                        "campaign_id": "campaign_alpha_001"
                    }
                ]
            }
        }
        
        return scenarios
    
    def generate_compliance_officer_data(self) -> Dict[str, Any]:
        """Generate test data for compliance officer scenarios"""
        
        scenarios = {
            "gdpr_compliance": {
                "name": "GDPR Data Protection Testing",
                "description": "EU citizen data processing validation",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "eu_citizen_interview.mp4",
                        "data_subject": "EU_citizen",
                        "lawful_basis": "consent",
                        "retention_period": "2_years",
                        "metadata": {
                            "data_subject_rights": ["access", "rectification", "erasure"],
                            "privacy_by_design": True,
                            "data_minimization": True,
                            "consent_timestamp": datetime.now().isoformat()
                        }
                    }
                ]
            },
            "sox_compliance": {
                "name": "SOX Financial Compliance Testing",
                "description": "Financial institution compliance validation",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "financial_earnings_call.mp4",
                        "financial_content": True,
                        "executive_communication": True,
                        "metadata": {
                            "internal_controls": "documented",
                            "management_certification": "required",
                            "disclosure_controls": "validated",
                            "audit_trail": "complete"
                        }
                    }
                ]
            },
            "hipaa_compliance": {
                "name": "HIPAA Healthcare Compliance Testing",
                "description": "Healthcare data protection validation",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "patient_consultation.mp4",
                        "phi_content": True,
                        "healthcare_context": True,
                        "metadata": {
                            "phi_protection": "encrypted",
                            "administrative_safeguards": "implemented",
                            "physical_safeguards": "validated",
                            "technical_safeguards": "verified"
                        }
                    }
                ]
            }
        }
        
        return scenarios
    
    def generate_content_moderator_data(self) -> Dict[str, Any]:
        """Generate test data for content moderator scenarios"""
        
        scenarios = {
            "misinformation_detection": {
                "name": "Misinformation Campaign Detection",
                "description": "Political and health misinformation deepfakes",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "political_misinformation_001.mp4",
                        "content_type": "political",
                        "misinformation_category": "election_interference",
                        "confidence_threshold": 0.85,
                        "metadata": {
                            "policy_violation": "misinformation",
                            "severity": "high",
                            "escalation_required": True,
                            "fact_check_status": "pending"
                        }
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "health_misinformation_001.mp4",
                        "content_type": "health",
                        "misinformation_category": "medical_advice",
                        "confidence_threshold": 0.90,
                        "metadata": {
                            "policy_violation": "health_misinformation",
                            "severity": "critical",
                            "escalation_required": True,
                            "medical_review_required": True
                        }
                    }
                ]
            },
            "harmful_content": {
                "name": "Harmful Content Detection",
                "description": "Non-consensual and harassment content",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": "harassment_content_001.mp4",
                        "content_type": "harassment",
                        "harm_category": "cyberbullying",
                        "confidence_threshold": 0.95,
                        "metadata": {
                            "policy_violation": "harassment",
                            "severity": "high",
                            "immediate_removal": True,
                            "user_report_integration": True
                        }
                    }
                ]
            },
            "bulk_processing": {
                "name": "High-Volume Content Processing",
                "description": "Large batch processing for efficiency testing",
                "test_files": [
                    {
                        "id": str(uuid.uuid4()),
                        "filename": f"batch_content_{i:03d}.mp4",
                        "batch_id": "bulk_test_001",
                        "processing_priority": random.choice(["low", "medium", "high"]),
                        "estimated_processing_time": random.uniform(2, 8)
                    }
                    for i in range(1, 101)  # Generate 100 test files
                ]
            }
        }
        
        return scenarios
    
    def generate_test_scenarios(self) -> Dict[str, Any]:
        """Generate comprehensive test scenarios for all personas"""
        
        all_scenarios = {
            "security_professionals": self.generate_security_professional_data(),
            "compliance_officers": self.generate_compliance_officer_data(),
            "content_moderators": self.generate_content_moderator_data()
        }
        
        # Add scenario metadata
        scenario_metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_scenarios": sum(len(persona_scenarios) for persona_scenarios in all_scenarios.values()),
            "total_test_files": sum(
                sum(len(scenario.get("test_files", [])) for scenario in persona_scenarios.values())
                for persona_scenarios in all_scenarios.values()
            ),
            "personas": list(all_scenarios.keys()),
            "version": "1.0"
        }
        
        return {
            "metadata": scenario_metadata,
            "scenarios": all_scenarios
        }
    
    def generate_evaluation_criteria(self) -> Dict[str, Any]:
        """Generate evaluation criteria and scoring matrices"""
        
        criteria = {
            "security_professionals": {
                "critical_metrics": {
                    "detection_accuracy": {"weight": 0.40, "min_score": 0.85, "target_score": 0.95},
                    "false_positive_rate": {"weight": 0.25, "max_rate": 0.02, "target_rate": 0.01},
                    "processing_speed": {"weight": 0.20, "max_time": 30, "target_time": 15},
                    "audit_trail_quality": {"weight": 0.15, "min_score": 0.90, "target_score": 0.95}
                },
                "acceptance_criteria": {
                    "overall_score": 0.90,
                    "critical_failures": 0,
                    "security_vulnerabilities": 0,
                    "compliance_violations": 0
                }
            },
            "compliance_officers": {
                "critical_metrics": {
                    "regulatory_compliance": {"weight": 0.50, "min_score": 0.95, "target_score": 1.00},
                    "audit_trail_coverage": {"weight": 0.30, "min_score": 0.90, "target_score": 0.95},
                    "risk_management": {"weight": 0.20, "min_score": 0.85, "target_score": 0.90}
                },
                "acceptance_criteria": {
                    "overall_score": 0.95,
                    "regulatory_violations": 0,
                    "audit_gaps": 0,
                    "compliance_gaps": 0
                }
            },
            "content_moderators": {
                "critical_metrics": {
                    "detection_accuracy": {"weight": 0.35, "min_score": 0.85, "target_score": 0.90},
                    "processing_speed": {"weight": 0.30, "max_time": 30, "target_time": 20},
                    "user_experience": {"weight": 0.20, "min_score": 0.85, "target_score": 0.90},
                    "safety_features": {"weight": 0.15, "min_score": 0.90, "target_score": 0.95}
                },
                "acceptance_criteria": {
                    "overall_score": 0.85,
                    "safety_failures": 0,
                    "performance_degradation": 0,
                    "user_satisfaction": 0.85
                }
            }
        }
        
        return criteria
    
    def generate_uat_report_template(self) -> Dict[str, Any]:
        """Generate UAT report templates for each persona"""
        
        templates = {
            "security_professionals": {
                "report_sections": [
                    "Executive Summary",
                    "Threat Detection Results",
                    "Incident Response Validation",
                    "System Security Assessment",
                    "Compliance Verification",
                    "Critical Findings",
                    "Recommendations",
                    "Approval Status"
                ],
                "required_metrics": [
                    "Overall Detection Accuracy",
                    "False Positive Rate",
                    "Processing Speed",
                    "System Uptime",
                    "Security Assessment Score"
                ]
            },
            "compliance_officers": {
                "report_sections": [
                    "Regulatory Compliance Summary",
                    "GDPR Compliance Assessment",
                    "SOX Compliance Validation",
                    "HIPAA Compliance Verification",
                    "Audit Trail Completeness",
                    "Risk Management Assessment",
                    "Compliance Gaps",
                    "Regulatory Approval"
                ],
                "required_metrics": [
                    "Regulatory Compliance Score",
                    "Audit Trail Coverage",
                    "Risk Mitigation Effectiveness",
                    "Documentation Completeness"
                ]
            },
            "content_moderators": {
                "report_sections": [
                    "Content Moderation Summary",
                    "Detection Performance",
                    "Processing Efficiency",
                    "User Experience Assessment",
                    "Safety Features Validation",
                    "Policy Enforcement Results",
                    "Moderator Feedback",
                    "Platform Readiness"
                ],
                "required_metrics": [
                    "Detection Accuracy",
                    "Processing Speed",
                    "User Satisfaction",
                    "Safety Feature Effectiveness"
                ]
            }
        }
        
        return templates
    
    def save_test_data(self) -> None:
        """Save all generated test data to files"""
        
        # Generate and save scenarios
        scenarios = self.generate_test_scenarios()
        with open(self.scenarios_dir / "uat_scenarios.json", "w") as f:
            json.dump(scenarios, f, indent=2)
        
        # Generate and save evaluation criteria
        criteria = self.generate_evaluation_criteria()
        with open(self.metadata_dir / "evaluation_criteria.json", "w") as f:
            json.dump(criteria, f, indent=2)
        
        # Generate and save report templates
        templates = self.generate_uat_report_template()
        with open(self.reports_dir / "report_templates.json", "w") as f:
            json.dump(templates, f, indent=2)
        
        # Generate test data summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_scenarios": scenarios["metadata"]["total_scenarios"],
            "total_test_files": scenarios["metadata"]["total_test_files"],
            "personas_covered": scenarios["metadata"]["personas"],
            "files_generated": [
                "uat_scenarios.json",
                "evaluation_criteria.json",
                "report_templates.json"
            ],
            "directories_created": [
                str(self.video_dir),
                str(self.metadata_dir),
                str(self.scenarios_dir),
                str(self.reports_dir)
            ]
        }
        
        with open(self.output_dir / "test_data_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ UAT test data generated successfully!")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📊 Total scenarios: {summary['total_scenarios']}")
        print(f"📁 Total test files: {summary['total_test_files']}")
        print(f"👥 Personas covered: {', '.join(summary['personas_covered'])}")
    
    def generate_csv_test_data(self) -> None:
        """Generate CSV files for easy import into testing tools"""
        
        # Generate test cases CSV
        test_cases = []
        scenarios = self.generate_test_scenarios()
        
        for persona, persona_scenarios in scenarios["scenarios"].items():
            for scenario_name, scenario_data in persona_scenarios.items():
                for test_file in scenario_data.get("test_files", []):
                    test_cases.append({
                        "persona": persona,
                        "scenario": scenario_name,
                        "test_id": test_file["id"],
                        "filename": test_file["filename"],
                        "technique": test_file.get("technique", "unknown"),
                        "confidence_threshold": test_file.get("confidence_threshold", 0.80),
                        "urgency": test_file.get("urgency", "medium"),
                        "description": scenario_data["description"]
                    })
        
        # Save test cases CSV
        with open(self.metadata_dir / "test_cases.csv", "w", newline="") as f:
            if test_cases:
                writer = csv.DictWriter(f, fieldnames=test_cases[0].keys())
                writer.writeheader()
                writer.writerows(test_cases)
        
        print(f"📊 Generated {len(test_cases)} test cases in CSV format")


def main():
    """Main function to generate UAT test data"""
    
    print("🚀 Generating UAT Test Data for SecureAI DeepFake Detection System")
    print("=" * 70)
    
    # Initialize generator
    generator = UATTestDataGenerator()
    
    # Generate and save all test data
    generator.save_test_data()
    generator.generate_csv_test_data()
    
    print("\n📋 UAT Test Data Generation Complete!")
    print("\nNext Steps:")
    print("1. Review generated scenarios in uat_test_data/scenarios/")
    print("2. Check evaluation criteria in uat_test_data/metadata/")
    print("3. Use report templates in uat_test_data/reports/")
    print("4. Import test cases from uat_test_data/metadata/test_cases.csv")
    print("\n🎯 Ready for User Acceptance Testing!")


if __name__ == "__main__":
    main()
