# File: hexstrike_reporting.py
"""
HexStrike Reporting Module
Generates professional penetration testing reports based on industry standards.
Ref: https://github.com/juliocesarfort/public-pentesting-reports/
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from hexstrike_persistence import get_persistence

class HexStrikeReporter:
    """
    Generates reports in various formats (Markdown, JSON) following 
    established pentesting company models.
    """
    
    TEMPLATES = {
        "standard": "HexStrike Standard Security Assessment",
        "ncc": "NCC Group Inspired Technical Report",
        "offsec": "Offensive Security Inspired Penetration Test Report",
        "minimal": "Executive Summary and Findings Table"
    }

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, "reports")
            
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.persistence = get_persistence()

    def generate_report(self, project_id: str, template: str = "standard") -> Dict[str, Any]:
        """Generate a complete report for a project."""
        project = self.persistence.get_project(project_id)
        if not project:
            return {"error": f"Project '{project_id}' not found."}

        findings = self.persistence.get_project_findings(project_id)
        sessions = self.persistence.get_project_sessions(project_id)
        
        report_data = {
            "project": project,
            "findings": findings,
            "sessions": sessions,
            "generated_at": datetime.now().isoformat(),
            "template": template
        }

        # Generate Markdown content
        md_content = self._build_markdown_report(report_data, template)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(x for x in project['name'] if x.isalnum() or x in " -_").strip().replace(" ", "_")
        filename = f"report_{safe_name}_{timestamp}.md"
        report_path = self.output_dir / filename
        
        with open(report_path, 'w') as f:
            f.write(md_content)

        return {
            "success": True,
            "project_id": project_id,
            "filename": filename,
            "path": str(report_path),
            "summary": {
                "total_findings": len(findings),
                "critical": len([f for f in findings if f.get('severity') == 'CRITICAL']),
                "high": len([f for f in findings if f.get('severity') == 'HIGH']),
                "medium": len([f for f in findings if f.get('severity') == 'MEDIUM']),
                "low": len([f for f in findings if f.get('severity') == 'LOW']),
                "info": len([f for f in findings if f.get('severity') == 'INFO'])
            }
        }

    def _build_markdown_report(self, data: Dict, template: str) -> str:
        """Constructs the Markdown string based on the chosen template."""
        project = data['project']
        findings = data['findings']
        
        # Sort findings by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4, None: 5}
        sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.get('severity'), 5))

        lines = []
        
        # Header
        lines.append(f"# {self.TEMPLATES.get(template, 'Security Assessment Report')}")
        lines.append(f"**Project:** {project['name']}")
        lines.append(f"**Target:** `{project['target']}`")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"**Framework:** HexStrike AI v6.0")
        lines.append("\n---\n")

        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("1. [Executive Summary](#1-executive-summary)")
        lines.append("2. [Project Scope](#2-project-scope)")
        lines.append("3. [Methodology](#3-methodology)")
        lines.append("4. [Findings Summary](#4-findings-summary)")
        lines.append("5. [Detailed Findings](#5-detailed-findings)")
        lines.append("6. [Remediation Roadmap](#6-remediation-roadmap)")
        lines.append("\n---\n")

        # 1. Executive Summary
        lines.append("## 1. Executive Summary")
        if template == "ncc":
            lines.append("This report summarizes the results of a time-limited security assessment. The primary objective was to identify security vulnerabilities and provide actionable remediation advice.")
        elif template == "offsec":
            lines.append("During the course of this engagement, a multi-stage attack path was discovered. Our assessment focused on demonstrating technical risk through Proof-of-Concept (PoC) exploits.")
        else:
            lines.append(f"HexStrike AI has completed a security assessment of {project['target']}. The assessment identified {len(findings)} unique findings.")
        
        # Findings count table
        lines.append("\n| Severity | Count |")
        lines.append("| :--- | :--- |")
        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            count = len([f for f in findings if f.get('severity') == sev])
            lines.append(f"| {sev} | {count} |")
        lines.append("\n")

        # 2. Project Scope
        lines.append("## 2. Project Scope")
        lines.append(f"The following assets were included in the assessment scope:")
        lines.append(f"- **Primary Target:** `{project['target']}`")
        if project.get('description'):
            lines.append(f"- **Description:** {project['description']}")
        lines.append("\n")

        # 3. Methodology
        lines.append("## 3. Methodology")
        lines.append("The assessment followed an AI-augmented penetration testing methodology consisting of the following phases:")
        lines.append("- **Reconnaissance:** Automated subdomain discovery and port scanning.")
        lines.append("- **Vulnerability Analysis:** Intelligent scanning and parameter fuzzing.")
        lines.append("- **Exploitation:** Demonstrating impact through safe Proof-of-Concepts.")
        lines.append("- **Reporting:** Correlation of findings and remediation planning.")
        lines.append("\n")

        # 4. Findings Summary
        lines.append("## 4. Findings Summary")
        lines.append("| ID | Severity | Title | Location |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for i, f in enumerate(sorted_findings):
            lines.append(f"| FIND-{i+1:03} | {f.get('severity', 'INFO')} | {f['title']} | `{f.get('location', 'N/A')}` |")
        lines.append("\n")

        # 5. Detailed Findings
        lines.append("## 5. Detailed Findings")
        for i, f in enumerate(sorted_findings):
            lines.append(f"### 5.{i+1} [FIND-{i+1:03}] {f['title']}")
            lines.append(f"**Severity:** {f.get('severity', 'INFO')}")
            if f.get('cve_id'):
                lines.append(f"**CVE:** {f['cve_id']}")
            lines.append(f"\n**Description:**\n{f.get('description', 'No description provided.')}")
            
            if f.get('evidence'):
                lines.append("\n**Technical Evidence / PoC:**")
                lines.append("```text")
                lines.append(f"{f['evidence']}")
                lines.append("```")
            
            if f.get('raw_data'):
                try:
                    raw = json.loads(f['raw_data'])
                    if 'remediation' in raw:
                        lines.append(f"\n**Remediation:**\n{raw['remediation']}")
                except:
                    pass
            
            lines.append("\n---\n")

        # 6. Remediation Roadmap
        lines.append("## 6. Remediation Roadmap")
        lines.append("Immediate actions suggested based on severity:")
        if any(f.get('severity') in ['CRITICAL', 'HIGH'] for f in findings):
            lines.append("1. **Urgent:** Address all CRITICAL and HIGH severity findings within 48-72 hours.")
        lines.append("2. **Short-term:** Patch MEDIUM severity findings during the next maintenance window.")
        lines.append("3. **Continuous:** Review LOW and INFO findings to improve overall security hygiene.")
        
        lines.append("\n\n*Generated by HexStrike AI Reporting Module*")
        
        return "\n".join(lines)

# Singleton instance
_reporter = None

def get_reporter() -> HexStrikeReporter:
    """Get singleton reporter instance"""
    global _reporter
    if _reporter is None:
        _reporter = HexStrikeReporter()
    return _reporter
