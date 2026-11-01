#!/usr/bin/env python3
"""
SecureAI DeepFake Detection System
ROI Calculator & Business Case Generator

This tool helps organizations calculate the ROI of implementing SecureAI
and generates comprehensive business case documentation.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime
import yaml

@dataclass
class OrganizationProfile:
    """Organization profile for ROI calculation"""
    name: str
    industry: str
    size: str  # small, medium, large, enterprise
    annual_revenue: float
    security_budget: float
    current_threat_level: str  # low, medium, high, critical

@dataclass
class ThreatMetrics:
    """Current threat exposure metrics"""
    deepfake_incidents_per_year: int
    average_incident_cost: float
    reputational_damage_cost: float
    compliance_violation_cost: float
    prevention_time_hours: float
    hourly_rate: float

@dataclass
class SecureAIInvestment:
    """SecureAI investment details"""
    tier: str  # starter, professional, enterprise
    monthly_cost: float
    annual_cost: float
    implementation_cost: float
    training_cost: float
    ongoing_costs: float

class ROICalculator:
    """Calculate ROI for SecureAI implementation"""
    
    def __init__(self):
        self.pricing = {
            "starter": {
                "monthly": 499,
                "annual": 4990,
                "analyses": 1000,
                "users": 6
            },
            "professional": {
                "monthly": 1999,
                "annual": 19990,
                "analyses": 5000,
                "users": 23
            },
            "enterprise": {
                "monthly": 7500,
                "annual": 75000,
                "analyses": "unlimited",
                "users": "unlimited"
            }
        }
        
        # Industry average costs
        self.industry_averages = {
            "financial_services": {
                "incident_cost": 350000,
                "incidents_per_year": 8,
                "prevention_hours": 500
            },
            "technology": {
                "incident_cost": 250000,
                "incidents_per_year": 6,
                "prevention_hours": 400
            },
            "healthcare": {
                "incident_cost": 400000,
                "incidents_per_year": 5,
                "prevention_hours": 450
            },
            "media": {
                "incident_cost": 200000,
                "incidents_per_year": 12,
                "prevention_hours": 600
            },
            "government": {
                "incident_cost": 500000,
                "incidents_per_year": 4,
                "prevention_hours": 300
            },
            "general": {
                "incident_cost": 250000,
                "incidents_per_year": 5,
                "prevention_hours": 400
            }
        }
    
    def calculate_roi(self, 
                     org_profile: OrganizationProfile,
                     threat_metrics: ThreatMetrics,
                     investment: SecureAIInvestment,
                     years: int = 3) -> Dict[str, Any]:
        """Calculate comprehensive ROI analysis"""
        
        # Calculate current costs (without SecureAI)
        current_annual_costs = self._calculate_current_costs(threat_metrics)
        
        # Calculate SecureAI costs
        secureai_costs = self._calculate_secureai_costs(investment, years)
        
        # Calculate cost savings
        cost_savings = self._calculate_cost_savings(
            current_annual_costs, 
            threat_metrics, 
            years
        )
        
        # Calculate productivity gains
        productivity_gains = self._calculate_productivity_gains(
            threat_metrics,
            years
        )
        
        # Calculate ROI metrics
        roi_metrics = self._calculate_roi_metrics(
            current_annual_costs,
            secureai_costs,
            cost_savings,
            productivity_gains,
            years
        )
        
        # Generate business case
        business_case = self._generate_business_case(
            org_profile,
            current_annual_costs,
            secureai_costs,
            roi_metrics,
            years
        )
        
        return {
            "organization": org_profile.__dict__,
            "current_costs": current_annual_costs,
            "secureai_costs": secureai_costs,
            "cost_savings": cost_savings,
            "productivity_gains": productivity_gains,
            "roi_metrics": roi_metrics,
            "business_case": business_case
        }
    
    def _calculate_current_costs(self, threat_metrics: ThreatMetrics) -> Dict[str, float]:
        """Calculate current annual costs without SecureAI"""
        
        # Direct incident costs
        incident_costs = (
            threat_metrics.deepfake_incidents_per_year * 
            threat_metrics.average_incident_cost
        )
        
        # Reputational damage
        reputational_costs = (
            threat_metrics.deepfake_incidents_per_year *
            threat_metrics.reputational_damage_cost
        )
        
        # Compliance violations
        compliance_costs = threat_metrics.compliance_violation_cost
        
        # Prevention time costs
        prevention_costs = (
            threat_metrics.prevention_time_hours *
            threat_metrics.hourly_rate
        )
        
        total_annual_cost = (
            incident_costs + 
            reputational_costs + 
            compliance_costs + 
            prevention_costs
        )
        
        return {
            "incident_costs": incident_costs,
            "reputational_costs": reputational_costs,
            "compliance_costs": compliance_costs,
            "prevention_costs": prevention_costs,
            "total_annual_cost": total_annual_cost
        }
    
    def _calculate_secureai_costs(self, 
                                  investment: SecureAIInvestment, 
                                  years: int) -> Dict[str, float]:
        """Calculate total SecureAI costs over specified period"""
        
        # First year costs
        first_year = (
            investment.annual_cost +
            investment.implementation_cost +
            investment.training_cost
        )
        
        # Subsequent years
        subsequent_years = (
            investment.annual_cost +
            investment.ongoing_costs
        ) * (years - 1)
        
        total_cost = first_year + subsequent_years
        
        return {
            "first_year": first_year,
            "annual_recurring": investment.annual_cost + investment.ongoing_costs,
            "total_cost": total_cost,
            "average_annual": total_cost / years
        }
    
    def _calculate_cost_savings(self,
                                current_costs: Dict[str, float],
                                threat_metrics: ThreatMetrics,
                                years: int) -> Dict[str, float]:
        """Calculate cost savings with SecureAI"""
        
        # Assume 90% reduction in deepfake incidents
        prevention_rate = 0.90
        
        # Calculate annual savings
        annual_incident_savings = (
            current_costs["incident_costs"] * prevention_rate
        )
        
        annual_reputational_savings = (
            current_costs["reputational_costs"] * prevention_rate
        )
        
        annual_compliance_savings = (
            current_costs["compliance_costs"] * 0.50  # 50% reduction
        )
        
        # Reduction in manual prevention time (70% reduction)
        annual_time_savings = (
            current_costs["prevention_costs"] * 0.70
        )
        
        total_annual_savings = (
            annual_incident_savings +
            annual_reputational_savings +
            annual_compliance_savings +
            annual_time_savings
        )
        
        return {
            "annual_incident_savings": annual_incident_savings,
            "annual_reputational_savings": annual_reputational_savings,
            "annual_compliance_savings": annual_compliance_savings,
            "annual_time_savings": annual_time_savings,
            "total_annual_savings": total_annual_savings,
            "total_savings_period": total_annual_savings * years
        }
    
    def _calculate_productivity_gains(self,
                                     threat_metrics: ThreatMetrics,
                                     years: int) -> Dict[str, float]:
        """Calculate productivity gains from automation"""
        
        # Time saved through automation
        annual_hours_saved = threat_metrics.prevention_time_hours * 0.70
        annual_cost_saved = annual_hours_saved * threat_metrics.hourly_rate
        
        # Additional productivity benefits
        faster_response_value = 50000  # Faster incident response
        better_accuracy_value = 25000  # Reduced false positives
        
        total_annual_gain = (
            annual_cost_saved +
            faster_response_value +
            better_accuracy_value
        )
        
        return {
            "hours_saved_annually": annual_hours_saved,
            "time_cost_savings": annual_cost_saved,
            "faster_response_value": faster_response_value,
            "better_accuracy_value": better_accuracy_value,
            "total_annual_gain": total_annual_gain,
            "total_gain_period": total_annual_gain * years
        }
    
    def _calculate_roi_metrics(self,
                              current_costs: Dict[str, float],
                              secureai_costs: Dict[str, float],
                              cost_savings: Dict[str, float],
                              productivity_gains: Dict[str, float],
                              years: int) -> Dict[str, Any]:
        """Calculate comprehensive ROI metrics"""
        
        # Total benefits
        total_benefits = (
            cost_savings["total_savings_period"] +
            productivity_gains["total_gain_period"]
        )
        
        # Total costs
        total_costs = secureai_costs["total_cost"]
        
        # Net benefit
        net_benefit = total_benefits - total_costs
        
        # ROI percentage
        roi_percentage = ((net_benefit / total_costs) * 100) if total_costs > 0 else 0
        
        # Payback period (in months)
        monthly_savings = cost_savings["total_annual_savings"] / 12
        payback_months = (
            secureai_costs["first_year"] / monthly_savings 
            if monthly_savings > 0 else float('inf')
        )
        
        # Break-even analysis
        break_even_month = payback_months
        
        return {
            "total_benefits": total_benefits,
            "total_costs": total_costs,
            "net_benefit": net_benefit,
            "roi_percentage": roi_percentage,
            "payback_months": payback_months,
            "break_even_month": break_even_month,
            "benefit_cost_ratio": total_benefits / total_costs if total_costs > 0 else 0,
            "annual_savings": cost_savings["total_annual_savings"],
            "monthly_savings": monthly_savings
        }
    
    def _generate_business_case(self,
                               org_profile: OrganizationProfile,
                               current_costs: Dict[str, float],
                               secureai_costs: Dict[str, float],
                               roi_metrics: Dict[str, Any],
                               years: int) -> str:
        """Generate executive business case summary"""
        
        business_case = f"""
SECUREAI DEEPFAKE DETECTION SYSTEM
BUSINESS CASE & ROI ANALYSIS

Organization: {org_profile.name}
Industry: {org_profile.industry}
Analysis Date: {datetime.now().strftime('%B %d, %Y')}
Analysis Period: {years} years

EXECUTIVE SUMMARY
================================================================================

Investment Recommendation: {'STRONGLY RECOMMENDED' if roi_metrics['roi_percentage'] > 100 else 'RECOMMENDED' if roi_metrics['roi_percentage'] > 50 else 'CONSIDER'}

Current Situation:
  Annual cost of deepfake threats: ${current_costs['total_annual_cost']:,.0f}
  Security team time spent on prevention: ${current_costs['prevention_costs']:,.0f}
  Potential compliance violations: ${current_costs['compliance_costs']:,.0f}

SecureAI Investment:
  Total investment ({years} years): ${secureai_costs['total_cost']:,.0f}
  Average annual cost: ${secureai_costs['average_annual']:,.0f}
  First year cost: ${secureai_costs['first_year']:,.0f}

Financial Impact:
  Total benefits ({years} years): ${roi_metrics['total_benefits']:,.0f}
  Net benefit: ${roi_metrics['net_benefit']:,.0f}
  ROI: {roi_metrics['roi_percentage']:.1f}%
  Payback period: {roi_metrics['payback_months']:.1f} months
  Benefit-cost ratio: {roi_metrics['benefit_cost_ratio']:.2f}:1

KEY FINDINGS
================================================================================

1. COST AVOIDANCE
   - Prevent 90% of deepfake incidents
   - Save ${roi_metrics['annual_savings']:,.0f} annually
   - Break even in {roi_metrics['break_even_month']:.1f} months

2. PRODUCTIVITY GAINS
   - Automate 70% of manual detection work
   - Save {roi_metrics['annual_savings'] / current_costs['total_annual_cost'] * 100:.1f}% of current security costs
   - Faster incident response and resolution

3. RISK REDUCTION
   - 95%+ detection accuracy
   - Reduce false positives
   - Comprehensive audit trail
   - Regulatory compliance built-in

4. COMPETITIVE ADVANTAGE
   - Industry-leading technology
   - Enhanced brand protection
   - Customer trust and confidence
   - Market differentiation

RECOMMENDATION
================================================================================

Based on this analysis, we recommend implementing SecureAI DeepFake Detection 
System. The {roi_metrics['roi_percentage']:.0f}% ROI and {roi_metrics['break_even_month']:.1f}-month payback period 
demonstrate clear financial value, while the risk reduction and productivity 
gains provide additional strategic benefits.

Next Steps:
1. Schedule demo with SecureAI sales team
2. Conduct technical evaluation
3. Plan pilot deployment
4. Develop implementation roadmap
5. Secure budget approval
"""
        return business_case
    
    def generate_report(self, roi_analysis: Dict[str, Any], format: str = "text") -> str:
        """Generate ROI report in specified format"""
        
        if format == "json":
            return json.dumps(roi_analysis, indent=2, default=str)
        elif format == "yaml":
            return yaml.dump(roi_analysis, default_flow_style=False)
        else:
            return roi_analysis["business_case"]
    
    def save_report(self, roi_analysis: Dict[str, Any], output_file: str):
        """Save ROI report to file"""
        
        # Determine format from file extension
        if output_file.endswith('.json'):
            format = "json"
        elif output_file.endswith('.yaml') or output_file.endswith('.yml'):
            format = "yaml"
        else:
            format = "text"
        
        report = self.generate_report(roi_analysis, format)
        
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"Report saved to: {output_file}")

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="SecureAI ROI Calculator and Business Case Generator"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--output",
        help="Output file for ROI report"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    calculator = ROICalculator()
    
    if args.interactive:
        # Interactive mode
        print("=" * 80)
        print("SecureAI ROI Calculator - Interactive Mode")
        print("=" * 80)
        print()
        
        # Gather organization information
        org_name = input("Organization name: ")
        industry = input("Industry (financial_services/technology/healthcare/media/government/general): ")
        size = input("Organization size (small/medium/large/enterprise): ")
        annual_revenue = float(input("Annual revenue ($): "))
        security_budget = float(input("Annual security budget ($): "))
        threat_level = input("Current threat level (low/medium/high/critical): ")
        
        # Use industry averages or custom inputs
        use_averages = input("Use industry average threat metrics? (yes/no): ").lower() == "yes"
        
        if use_averages and industry in calculator.industry_averages:
            averages = calculator.industry_averages[industry]
            incidents = averages["incidents_per_year"]
            incident_cost = averages["incident_cost"]
            prevention_hours = averages["prevention_hours"]
        else:
            incidents = int(input("Deepfake incidents per year: "))
            incident_cost = float(input("Average cost per incident ($): "))
            prevention_hours = float(input("Hours spent on manual prevention per year: "))
        
        reputational_damage = float(input("Estimated reputational damage per incident ($): ") or "0")
        compliance_violation = float(input("Annual compliance violation costs ($): ") or "0")
        hourly_rate = float(input("Average security team hourly rate ($): ") or "150")
        
        # SecureAI tier selection
        print("\nSecureAI Pricing Tiers:")
        print("1. Starter - $499/month ($4,990/year)")
        print("2. Professional - $1,999/month ($19,990/year)")
        print("3. Enterprise - Custom pricing (estimate $75,000/year)")
        
        tier_choice = input("Select tier (1/2/3): ")
        tier_map = {"1": "starter", "2": "professional", "3": "enterprise"}
        tier = tier_map.get(tier_choice, "professional")
        
        # Additional costs
        implementation = float(input("Implementation/setup cost estimate ($): ") or "5000")
        training = float(input("Training cost estimate ($): ") or "3000")
        ongoing = float(input("Ongoing costs per year ($): ") or "2000")
        
        analysis_years = int(input("Analysis period (years): ") or "3")
        
        # Create data objects
        org_profile = OrganizationProfile(
            name=org_name,
            industry=industry,
            size=size,
            annual_revenue=annual_revenue,
            security_budget=security_budget,
            current_threat_level=threat_level
        )
        
        threat_metrics = ThreatMetrics(
            deepfake_incidents_per_year=incidents,
            average_incident_cost=incident_cost,
            reputational_damage_cost=reputational_damage,
            compliance_violation_cost=compliance_violation,
            prevention_time_hours=prevention_hours,
            hourly_rate=hourly_rate
        )
        
        tier_pricing = calculator.pricing[tier]
        investment = SecureAIInvestment(
            tier=tier,
            monthly_cost=tier_pricing["monthly"],
            annual_cost=tier_pricing["annual"],
            implementation_cost=implementation,
            training_cost=training,
            ongoing_costs=ongoing
        )
        
        # Calculate ROI
        roi_analysis = calculator.calculate_roi(
            org_profile,
            threat_metrics,
            investment,
            analysis_years
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("ROI ANALYSIS RESULTS")
        print("=" * 80)
        print(roi_analysis["business_case"])
        
        # Save report if requested
        if args.output:
            calculator.save_report(roi_analysis, args.output)
    
    elif args.config:
        # Load from config file
        print(f"Loading configuration from: {args.config}")
        # Implementation would load config and calculate ROI
    else:
        # Quick example calculation
        print("=" * 80)
        print("SecureAI ROI Calculator - Example Calculation")
        print("=" * 80)
        print()
        print("Running example calculation for a medium-sized financial services firm...")
        print()
        
        org_profile = OrganizationProfile(
            name="Example Financial Corp",
            industry="financial_services",
            size="medium",
            annual_revenue=50000000,
            security_budget=1000000,
            current_threat_level="high"
        )
        
        threat_metrics = ThreatMetrics(
            deepfake_incidents_per_year=5,
            average_incident_cost=250000,
            reputational_damage_cost=100000,
            compliance_violation_cost=200000,
            prevention_time_hours=500,
            hourly_rate=150
        )
        
        investment = SecureAIInvestment(
            tier="professional",
            monthly_cost=1999,
            annual_cost=19990,
            implementation_cost=10000,
            training_cost=5000,
            ongoing_costs=2000
        )
        
        roi_analysis = calculator.calculate_roi(
            org_profile,
            threat_metrics,
            investment,
            years=3
        )
        
        print(roi_analysis["business_case"])
        
        if args.output:
            calculator.save_report(roi_analysis, args.output)

if __name__ == "__main__":
    main()
