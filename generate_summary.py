#!/usr/bin/env python3
"""
AI TestGen Summary Generator

Generates a comprehensive JSON summary of the pipeline execution,
including coverage metrics, test results, and execution details.

Usage:
    python generate_summary.py [--output summary.json]
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class SummaryGenerator:
    """Generates comprehensive pipeline summary from various output files."""
    
    def __init__(self, workspace_dir: str = "."):
        self.workspace = Path(workspace_dir)
        self.summary: Dict[str, Any] = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "1.0.0",
            "status": "unknown"
        }
    
    def parse_coverage_xml(self) -> Optional[Dict[str, Any]]:
        """Parse coverage.xml for coverage metrics."""
        coverage_file = self.workspace / "coverage.xml"
        if not coverage_file.exists():
            return None
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            line_rate = float(root.attrib.get("line-rate", 0))
            branch_rate = float(root.attrib.get("branch-rate", 0))
            
            # Get per-file coverage
            files_coverage = []
            for package in root.findall(".//package"):
                for cls in package.findall(".//class"):
                    filename = cls.attrib.get("filename", "")
                    file_line_rate = float(cls.attrib.get("line-rate", 0))
                    files_coverage.append({
                        "file": filename,
                        "coverage": round(file_line_rate * 100, 2)
                    })
            
            return {
                "line_coverage": round(line_rate * 100, 2),
                "branch_coverage": round(branch_rate * 100, 2),
                "files": files_coverage
            }
        except Exception as e:
            print(f"Warning: Failed to parse coverage.xml: {e}", file=sys.stderr)
            return None
    
    def parse_pytest_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Parse pytest JSON report."""
        json_file = self.workspace / filename
        if not json_file.exists():
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get("summary", {})
            return {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "errors": summary.get("error", 0),
                "duration": data.get("duration", 0)
            }
        except Exception as e:
            print(f"Warning: Failed to parse {filename}: {e}", file=sys.stderr)
            return None
    
    def parse_manual_test_result(self) -> Optional[Dict[str, Any]]:
        """Parse manual_test_result.json."""
        json_file = self.workspace / "manual_test_result.json"
        if not json_file.exists():
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            return {
                "found": data.get("manual_tests_found", False),
                "count": data.get("test_files_count", 0),
                "test_root": data.get("test_root", "")
            }
        except Exception as e:
            print(f"Warning: Failed to parse manual_test_result.json: {e}", file=sys.stderr)
            return None
    
    def count_generated_tests(self) -> int:
        """Count generated test files."""
        generated_dir = self.workspace / "tests" / "generated"
        if not generated_dir.exists():
            return 0
        
        return len(list(generated_dir.glob("**/test_*.py")))
    
    def parse_auto_fixer_report(self) -> Optional[Dict[str, Any]]:
        """Parse auto_fixer_report.json."""
        json_file = self.workspace / "auto_fixer_report.json"
        if not json_file.exists():
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            return {
                "iterations": data.get("iteration_count", 0),
                "successful_fixes": data.get("successful_fixes", 0),
                "failed_fixes": data.get("failed_fixes", 0),
                "code_bugs": data.get("code_bugs", 0)
            }
        except Exception as e:
            print(f"Warning: Failed to parse auto_fixer_report.json: {e}", file=sys.stderr)
            return None
    
    def parse_coverage_gaps(self) -> Optional[Dict[str, Any]]:
        """Parse coverage_gaps.json."""
        json_file = self.workspace / "coverage_gaps.json"
        if not json_file.exists():
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            total_gaps = data.get("total_uncovered_functions", 0)
            return {
                "total_uncovered_functions": total_gaps,
                "files_with_gaps": len(data.get("files", {}))
            }
        except Exception as e:
            print(f"Warning: Failed to parse coverage_gaps.json: {e}", file=sys.stderr)
            return None
    
    def generate(self) -> Dict[str, Any]:
        """Generate complete summary."""
        
        # Parse all available data sources
        coverage_data = self.parse_coverage_xml()
        manual_tests = self.parse_manual_test_result()
        auto_fixer = self.parse_auto_fixer_report()
        coverage_gaps = self.parse_coverage_gaps()
        
        # Try to get test results from different pytest JSON files
        test_results = (
            self.parse_pytest_json(".pytest_combined.json") or
            self.parse_pytest_json(".pytest_manual.json") or
            self.parse_pytest_json(".pytest_generated.json")
        )
        
        # Count generated tests
        generated_count = self.count_generated_tests()
        
        # Build summary
        self.summary["coverage"] = coverage_data or {"line_coverage": 0, "branch_coverage": 0}
        
        self.summary["tests"] = {
            "manual": manual_tests or {"found": False, "count": 0},
            "generated": {
                "count": generated_count
            },
            "results": test_results or {"total": 0, "passed": 0, "failed": 0}
        }
        
        if auto_fixer:
            self.summary["auto_fixer"] = auto_fixer
        
        if coverage_gaps:
            self.summary["coverage_gaps"] = coverage_gaps
        
        # Determine overall status
        if coverage_data and coverage_data.get("line_coverage", 0) > 0:
            if test_results and test_results.get("failed", 0) == 0:
                self.summary["status"] = "success"
            else:
                self.summary["status"] = "completed_with_failures"
        else:
            self.summary["status"] = "failed"
        
        # Create human-readable summary text
        coverage_pct = self.summary["coverage"].get("line_coverage", 0)
        tests_passed = self.summary["tests"]["results"].get("passed", 0)
        tests_failed = self.summary["tests"]["results"].get("failed", 0)
        
        self.summary["summary_text"] = (
            f"Generated {generated_count} tests, "
            f"coverage {coverage_pct:.1f}%, "
            f"{tests_passed} passed, {tests_failed} failed"
        )
        
        return self.summary
    
    def save(self, output_file: str = "summary.json"):
        """Save summary to JSON file."""
        output_path = self.workspace / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.summary, f, indent=2)
        
        print(f"Summary saved to: {output_path}")
        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate AI TestGen pipeline summary"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--output",
        default="summary.json",
        help="Output file name (default: summary.json)"
    )
    
    args = parser.parse_args()
    
    # Generate summary
    generator = SummaryGenerator(args.workspace)
    summary = generator.generate()
    
    # Print to console
    print("\n" + "="*60)
    print("AI TestGen Pipeline Summary")
    print("="*60)
    print(json.dumps(summary, indent=2))
    print("="*60 + "\n")
    
    # Save to file
    generator.save(args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
