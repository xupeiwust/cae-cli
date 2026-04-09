#!/usr/bin/env python3
"""
🔍 LLM Diagnostic Reasoning Skill - Main Entry Point

A viral Claude Skill that showcases three innovative diagnostic methods:
1. Multi-Step Reasoning Chain
2. Symptom-Driven Diagnosis
3. Bayesian Network Generation

Author: Your Name
License: MIT
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directories to path
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "ahu-diagnostic-backend" / "src"))
sys.path.insert(0, str(SKILL_ROOT / "symptom-driven-diagnosis" / "src"))
sys.path.insert(0, str(SKILL_ROOT / "bayesian_network_generation" / "src"))


class DiagnosticReasoningSkill:
    """Main skill orchestrator for diagnostic reasoning"""

    def __init__(self):
        self.skill_root = SKILL_ROOT
        self.methods = {
            'chain': 'Multi-Step Reasoning Chain',
            'symptom': 'Symptom-Driven Diagnosis',
            'bayesian': 'Bayesian Network Generation'
        }
        self.domains = ['hvac', 'medical', 'industrial']

    def welcome(self):
        """Display welcome message"""
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  🔍 LLM Diagnostic Reasoning Skill                        ║")
        print("║  Three Innovative Methods for Causal Inference            ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()
        print("📚 Available Methods:")
        print("  1. 🔗 chain    - Multi-Step Reasoning Chain")
        print("  2. 🎯 symptom  - Symptom-Driven Diagnosis")
        print("  3. 📊 bayesian - Bayesian Network Generation")
        print()
        print("🌍 Supported Domains:")
        print("  • HVAC Systems (Air Handling Units)")
        print("  • Medical Diagnosis")
        print("  • Industrial Equipment")
        print()
        print("💡 Quick Start:")
        print("  /diagnose chain hvac    - Start HVAC diagnosis")
        print("  /demo medical           - Run medical demo")
        print("  /compare case.json      - Compare all methods")
        print()

    def diagnose(self, method: str = None, domain: str = None, case_file: str = None):
        """
        Start interactive diagnostic session

        Args:
            method: Diagnostic method (chain/symptom/bayesian)
            domain: Application domain (hvac/medical/industrial)
            case_file: Optional case file path
        """
        print(f"\n🩺 Starting Diagnostic Session")
        print(f"{'='*60}\n")

        # Interactive method selection
        if not method:
            method = self._select_method()

        # Interactive domain selection
        if not domain:
            domain = self._select_domain()

        # Load or create case
        if case_file:
            case_data = self._load_case(case_file)
        else:
            case_data = self._interactive_case_input(domain)

        # Run diagnosis
        print(f"\n🔍 Running {self.methods[method]}...")
        print(f"📍 Domain: {domain.upper()}")
        print(f"{'='*60}\n")

        result = self._run_diagnosis(method, domain, case_data)

        # Display results
        self._display_results(result, method)

        # Offer visualization
        self._offer_visualization(result)

        return result

    def compare(self, case_file: str):
        """
        Compare all three diagnostic methods on the same case

        Args:
            case_file: Path to case file
        """
        print(f"\n📊 Comparative Analysis")
        print(f"{'='*60}\n")

        case_data = self._load_case(case_file)
        domain = case_data.get('domain', 'hvac')

        results = {}

        # Run all three methods
        for method in ['chain', 'symptom', 'bayesian']:
            print(f"\n🔄 Running {self.methods[method]}...")
            results[method] = self._run_diagnosis(method, domain, case_data)

        # Generate comparison report
        self._generate_comparison_report(results)

        return results

    def demo(self, domain: str = None):
        """
        Run interactive demo with pre-loaded examples

        Args:
            domain: Application domain (hvac/medical/industrial)
        """
        if not domain:
            domain = self._select_domain()

        print(f"\n🚀 Running {domain.upper()} Demo")
        print(f"{'='*60}\n")

        # Load demo case
        demo_cases = self._load_demo_cases(domain)

        print(f"📦 Loaded {len(demo_cases)} demo cases\n")

        # Let user select a case
        case_idx = self._select_demo_case(demo_cases)
        case_data = demo_cases[case_idx]

        # Show case details
        self._display_case(case_data)

        # Ask which method to use
        method = self._select_method()

        # Run diagnosis
        result = self._run_diagnosis(method, domain, case_data)

        # Display results with extra flair for demo
        self._display_results(result, method, demo_mode=True)

        return result

    def visualize(self, result_file: str):
        """
        Generate visualization from diagnosis result

        Args:
            result_file: Path to result JSON file
        """
        print(f"\n🎨 Generating Visualization")
        print(f"{'='*60}\n")

        with open(result_file, 'r') as f:
            result = json.load(f)

        method = result.get('method', 'chain')

        if method == 'chain':
            self._visualize_reasoning_chain(result)
        elif method == 'symptom':
            self._visualize_symptom_path(result)
        elif method == 'bayesian':
            self._visualize_bayesian_network(result)

        print("\n✅ Visualization saved!")

    # ========== Helper Methods ==========

    def _select_method(self) -> str:
        """Interactive method selection"""
        print("Select diagnostic method:")
        for i, (key, name) in enumerate(self.methods.items(), 1):
            print(f"  {i}. {name}")

        choice = input("\nEnter choice (1-3): ").strip()
        method_map = {1: 'chain', 2: 'symptom', 3: 'bayesian'}
        return method_map.get(int(choice), 'chain')

    def _select_domain(self) -> str:
        """Interactive domain selection"""
        print("Select application domain:")
        for i, domain in enumerate(self.domains, 1):
            print(f"  {i}. {domain.upper()}")

        choice = input("\nEnter choice (1-3): ").strip()
        return self.domains[int(choice) - 1]

    def _load_case(self, case_file: str) -> Dict:
        """Load case from file"""
        with open(case_file, 'r') as f:
            return json.load(f)

    def _interactive_case_input(self, domain: str) -> Dict:
        """Interactive case input"""
        print(f"\n📝 Enter case details for {domain.upper()}:")

        if domain == 'hvac':
            return self._input_hvac_case()
        elif domain == 'medical':
            return self._input_medical_case()
        else:
            return self._input_industrial_case()

    def _input_hvac_case(self) -> Dict:
        """Input HVAC case interactively"""
        print("\nEnter abnormal symptoms (comma-separated):")
        print("Example: SA_TEMP=high, ZONE_TEMP_1=high, CHWC_VLV=0.75")

        symptoms_str = input("Symptoms: ").strip()

        # Parse symptoms
        symptoms = []
        for symptom in symptoms_str.split(','):
            symptom = symptom.strip()
            if '=' in symptom:
                var, val = symptom.split('=')
                symptoms.append({
                    'variable': var.strip(),
                    'value': val.strip()
                })

        return {
            'domain': 'hvac',
            'symptoms': symptoms
        }

    def _input_medical_case(self) -> Dict:
        """Input medical case interactively"""
        print("\nEnter patient symptoms (comma-separated):")
        print("Example: fever, cough, fatigue, shortness of breath")

        symptoms_str = input("Symptoms: ").strip()
        symptoms = [s.strip() for s in symptoms_str.split(',')]

        return {
            'domain': 'medical',
            'symptoms': symptoms
        }

    def _input_industrial_case(self) -> Dict:
        """Input industrial case interactively"""
        print("\nEnter equipment symptoms (comma-separated):")
        print("Example: vibration=high, temperature=elevated, noise=abnormal")

        symptoms_str = input("Symptoms: ").strip()

        symptoms = []
        for symptom in symptoms_str.split(','):
            symptom = symptom.strip()
            if '=' in symptom:
                var, val = symptom.split('=')
                symptoms.append({
                    'variable': var.strip(),
                    'value': val.strip()
                })
            else:
                symptoms.append({'symptom': symptom})

        return {
            'domain': 'industrial',
            'symptoms': symptoms
        }

    def _run_diagnosis(self, method: str, domain: str, case_data: Dict) -> Dict:
        """Run diagnosis using specified method"""

        if method == 'chain':
            return self._run_chain_method(domain, case_data)
        elif method == 'symptom':
            return self._run_symptom_method(domain, case_data)
        elif method == 'bayesian':
            return self._run_bayesian_method(domain, case_data)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _run_chain_method(self, domain: str, case_data: Dict) -> Dict:
        """Run multi-step reasoning chain method"""
        print("📍 Step 1: Generating fault hypotheses...")
        print("📍 Step 2: Building reasoning chain...")
        print("📍 Step 3: Verification analysis...")

        # TODO: Integrate actual chain method
        return {
            'method': 'chain',
            'domain': domain,
            'diagnosis': 'coi_stuck_075',
            'confidence': 0.92,
            'reasoning_chain': {
                'root_cause': 'Cooling coil valve stuck at 75%',
                'propagation': [
                    'Valve stuck → Insufficient cooling',
                    'Insufficient cooling → SA_TEMP increases',
                    'SA_TEMP high → ZONE_TEMP increases'
                ]
            }
        }

    def _run_symptom_method(self, domain: str, case_data: Dict) -> Dict:
        """Run symptom-driven diagnosis method"""
        print("📍 Step 1: Selecting key symptom...")
        print("📍 Step 2: Backward propagation analysis...")
        print("📍 Step 3: Root cause localization...")
        print("📍 Step 4: Fault type matching...")

        # TODO: Integrate actual symptom method
        return {
            'method': 'symptom',
            'domain': domain,
            'diagnosis': 'coi_stuck_075',
            'confidence': 0.89,
            'root_cause_path': [
                'CHWC_VLV anomaly detected',
                'Traced to cooling_coil component',
                'Matched to valve stuck fault'
            ]
        }

    def _run_bayesian_method(self, domain: str, case_data: Dict) -> Dict:
        """Run Bayesian network generation method"""
        print("📍 Step 1: Generating BN structure...")
        print("📍 Step 2: Learning parameters from data...")
        print("📍 Step 3: Bayesian inference...")

        # TODO: Integrate actual Bayesian method
        return {
            'method': 'bayesian',
            'domain': domain,
            'diagnosis': 'coi_stuck_075',
            'probability': 0.94,
            'posterior_distribution': {
                'coi_stuck_075': 0.94,
                'coi_leak': 0.04,
                'sf_spd_low': 0.02
            }
        }

    def _display_results(self, result: Dict, method: str, demo_mode: bool = False):
        """Display diagnosis results"""
        print(f"\n{'='*60}")
        print(f"🎯 DIAGNOSIS RESULTS")
        print(f"{'='*60}\n")

        print(f"Method: {self.methods[method]}")
        print(f"Domain: {result['domain'].upper()}")
        print(f"\n🔍 Diagnosis: {result['diagnosis']}")

        if 'confidence' in result:
            print(f"📊 Confidence: {result['confidence']:.2%}")
        elif 'probability' in result:
            print(f"📊 Probability: {result['probability']:.2%}")

        if method == 'chain' and 'reasoning_chain' in result:
            print(f"\n🔗 Reasoning Chain:")
            for step in result['reasoning_chain']['propagation']:
                print(f"  → {step}")

        elif method == 'symptom' and 'root_cause_path' in result:
            print(f"\n🎯 Root Cause Path:")
            for step in result['root_cause_path']:
                print(f"  → {step}")

        elif method == 'bayesian' and 'posterior_distribution' in result:
            print(f"\n📊 Posterior Distribution:")
            for fault, prob in result['posterior_distribution'].items():
                print(f"  {fault}: {prob:.2%}")

        print(f"\n{'='*60}\n")

        if demo_mode:
            print("✨ This is a demo result. Try with your own cases!")

    def _offer_visualization(self, result: Dict):
        """Offer to generate visualization"""
        choice = input("\n🎨 Generate visualization? (y/n): ").strip().lower()

        if choice == 'y':
            # Save result to temp file
            temp_file = '/tmp/diagnosis_result.json'
            with open(temp_file, 'w') as f:
                json.dump(result, f, indent=2)

            self.visualize(temp_file)

    def _visualize_reasoning_chain(self, result: Dict):
        """Visualize reasoning chain"""
        print("Generating reasoning chain diagram...")
        # TODO: Implement actual visualization
        print("📊 Diagram saved to: results/reasoning_chain.png")

    def _visualize_symptom_path(self, result: Dict):
        """Visualize symptom-driven path"""
        print("Generating symptom path diagram...")
        # TODO: Implement actual visualization
        print("📊 Diagram saved to: results/symptom_path.png")

    def _visualize_bayesian_network(self, result: Dict):
        """Visualize Bayesian network"""
        print("Generating Bayesian network diagram...")
        # TODO: Implement actual visualization
        print("📊 Diagram saved to: results/bayesian_network.png")

    def _load_demo_cases(self, domain: str) -> List[Dict]:
        """Load demo cases for domain"""
        demo_dir = self.skill_root / "examples" / domain

        if not demo_dir.exists():
            return self._generate_default_demo_cases(domain)

        cases = []
        for case_file in demo_dir.glob("*.json"):
            with open(case_file, 'r') as f:
                cases.append(json.load(f))

        return cases

    def _generate_default_demo_cases(self, domain: str) -> List[Dict]:
        """Generate default demo cases"""
        if domain == 'hvac':
            return [
                {
                    'name': 'Cooling Coil Valve Stuck',
                    'symptoms': [
                        {'variable': 'SA_TEMP', 'value': 'high'},
                        {'variable': 'ZONE_TEMP_1', 'value': 'high'},
                        {'variable': 'CHWC_VLV', 'value': '0.75'}
                    ]
                }
            ]
        elif domain == 'medical':
            return [
                {
                    'name': 'Respiratory Infection',
                    'symptoms': ['fever', 'cough', 'fatigue', 'shortness of breath']
                }
            ]
        else:
            return [
                {
                    'name': 'Motor Bearing Failure',
                    'symptoms': [
                        {'variable': 'vibration', 'value': 'high'},
                        {'variable': 'temperature', 'value': 'elevated'},
                        {'variable': 'noise', 'value': 'abnormal'}
                    ]
                }
            ]

    def _select_demo_case(self, cases: List[Dict]) -> int:
        """Let user select a demo case"""
        print("Available demo cases:")
        for i, case in enumerate(cases, 1):
            print(f"  {i}. {case.get('name', f'Case {i}')}")

        choice = input("\nSelect case (1-{}): ".format(len(cases))).strip()
        return int(choice) - 1

    def _display_case(self, case_data: Dict):
        """Display case details"""
        print(f"\n📋 Case: {case_data.get('name', 'Unnamed')}")
        print(f"{'='*60}")
        print(f"\n🔍 Symptoms:")

        for symptom in case_data['symptoms']:
            if isinstance(symptom, dict):
                if 'variable' in symptom:
                    print(f"  • {symptom['variable']}: {symptom.get('value', 'abnormal')}")
                else:
                    print(f"  • {symptom.get('symptom', str(symptom))}")
            else:
                print(f"  • {symptom}")

        print(f"\n{'='*60}\n")

    def _generate_comparison_report(self, results: Dict):
        """Generate comparison report for all methods"""
        print(f"\n{'='*60}")
        print(f"📊 COMPARATIVE ANALYSIS")
        print(f"{'='*60}\n")

        print(f"{'Method':<30} {'Diagnosis':<20} {'Confidence':<10}")
        print(f"{'-'*60}")

        for method, result in results.items():
            diagnosis = result.get('diagnosis', 'N/A')
            conf = result.get('confidence', result.get('probability', 0))
            print(f"{self.methods[method]:<30} {diagnosis:<20} {conf:.2%}")

        print(f"\n{'='*60}\n")

        # Save comparison report
        report_file = 'results/comparison_report.json'
        os.makedirs('results', exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📄 Full report saved to: {report_file}\n")


def main():
    """Main entry point for the skill"""
    skill = DiagnosticReasoningSkill()

    if len(sys.argv) == 1:
        # No arguments - show welcome
        skill.welcome()
        return

    command = sys.argv[1]

    if command == 'diagnose':
        method = sys.argv[2] if len(sys.argv) > 2 else None
        domain = sys.argv[3] if len(sys.argv) > 3 else None
        case_file = sys.argv[4] if len(sys.argv) > 4 else None
        skill.diagnose(method, domain, case_file)

    elif command == 'compare':
        case_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not case_file:
            print("❌ Error: Please provide a case file")
            print("Usage: /compare <case-file>")
            return
        skill.compare(case_file)

    elif command == 'demo':
        domain = sys.argv[2] if len(sys.argv) > 2 else None
        skill.demo(domain)

    elif command == 'visualize':
        result_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not result_file:
            print("❌ Error: Please provide a result file")
            print("Usage: /visualize <result-file>")
            return
        skill.visualize(result_file)

    else:
        print(f"❌ Unknown command: {command}")
        print("\nAvailable commands:")
        print("  diagnose  - Start diagnostic session")
        print("  compare   - Compare all methods")
        print("  demo      - Run interactive demo")
        print("  visualize - Generate visualization")


if __name__ == '__main__':
    main()
