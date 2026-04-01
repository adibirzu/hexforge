# File: hexstrike_optimizer.py
"""
Token optimization for HexStrike responses.
Post-processes responses without modifying existing output generation.
"""

from typing import Dict, Any, List, Optional
import json
import re


class ResponseOptimizer:
    """
    Optimizes responses to reduce token usage.
    Works as a post-processor on existing responses.
    """

    # Response detail tiers
    TIERS = {
        'minimal': {
            'max_stdout_lines': 10,
            'max_findings': 3,
            'include_raw': False,
            'include_evidence': False
        },
        'summary': {
            'max_stdout_lines': 50,
            'max_findings': 10,
            'include_raw': False,
            'include_evidence': True
        },
        'detailed': {
            'max_stdout_lines': 200,
            'max_findings': 50,
            'include_raw': True,
            'include_evidence': True
        },
        'full': {
            'max_stdout_lines': None,
            'max_findings': None,
            'include_raw': True,
            'include_evidence': True
        }
    }

    def optimize_response(self, response: Dict, tier: str = 'summary') -> Dict:
        """
        Optimize response based on tier level.
        Does not modify original response, returns optimized copy.
        """
        config = self.TIERS.get(tier, self.TIERS['summary'])
        optimized = response.copy()

        # Truncate stdout
        if 'stdout' in optimized and config['max_stdout_lines']:
            optimized['stdout'] = self._truncate_output(
                optimized['stdout'],
                config['max_stdout_lines']
            )

        # Limit findings
        if 'findings' in optimized and config['max_findings']:
            optimized['findings'] = optimized['findings'][:config['max_findings']]
            if len(response.get('findings', [])) > config['max_findings']:
                optimized['findings_truncated'] = True
                optimized['total_findings'] = len(response['findings'])

        # Remove raw data if not needed
        if not config['include_raw']:
            optimized.pop('raw_output', None)
            optimized.pop('raw_data', None)

        return optimized

    def _truncate_output(self, output: str, max_lines: int) -> str:
        """Truncate output to max lines"""
        if not output:
            return output

        lines = output.split('\n')
        if len(lines) <= max_lines:
            return output

        # Keep first and last portions
        head = lines[:max_lines // 2]
        tail = lines[-(max_lines // 2):]
        truncated = len(lines) - max_lines

        return '\n'.join(head) + f'\n\n... [{truncated} lines truncated] ...\n\n' + '\n'.join(tail)

    def compress_findings(self, findings: List[Dict], max_tokens: int = 500) -> str:
        """Compress findings list to summary text"""
        if not findings:
            return "No findings."

        # Group by severity
        by_severity = {}
        for f in findings:
            sev = f.get('severity', 'UNKNOWN')
            by_severity.setdefault(sev, []).append(f)

        lines = []
        token_estimate = 0

        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            if sev not in by_severity:
                continue

            for finding in by_severity[sev]:
                line = f"[{sev}] {finding.get('title', 'Unknown')}"
                if finding.get('location'):
                    line += f" @ {finding['location']}"

                # Rough token estimate (words * 1.3)
                tokens = len(line.split()) * 1.3
                if token_estimate + tokens > max_tokens:
                    lines.append(f"... and {len(findings) - len(lines)} more")
                    break

                lines.append(line)
                token_estimate += tokens

        return '\n'.join(lines)

    def create_incremental_update(self, previous: Dict, current: Dict) -> Dict:
        """
        Create incremental update (only changed data).
        Reduces tokens when context hasn't changed much.
        """
        if not previous:
            return current

        delta = {'_type': 'incremental'}

        for key, value in current.items():
            if key not in previous:
                delta[key] = value
            elif previous[key] != value:
                if isinstance(value, list) and isinstance(previous.get(key), list):
                    # For lists, only include new items
                    prev_set = set(json.dumps(x, sort_keys=True) for x in previous[key])
                    new_items = [x for x in value if json.dumps(x, sort_keys=True) not in prev_set]
                    if new_items:
                        delta[f'{key}_new'] = new_items
                        delta[f'{key}_count'] = len(value)
                else:
                    delta[key] = value

        return delta


class ContextManager:
    """
    Manages context to minimize repetition across requests.
    """

    def __init__(self):
        self.session_contexts = {}  # session_id -> context

    def get_context(self, session_id: str) -> Dict:
        """Get current context for session"""
        return self.session_contexts.get(session_id, {})

    def update_context(self, session_id: str, updates: Dict):
        """Update session context"""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {}
        self.session_contexts[session_id].update(updates)

    def get_context_summary(self, session_id: str, max_tokens: int = 200) -> str:
        """Get compressed context summary"""
        context = self.get_context(session_id)
        if not context:
            return "No previous context."

        summary_parts = []
        token_estimate = 0

        if 'target' in context:
            summary_parts.append(f"Target: {context['target']}")

        if 'technologies' in context:
            techs = context['technologies'][:5]  # Top 5
            summary_parts.append(f"Technologies: {', '.join(techs)}")

        if 'findings_count' in context:
            summary_parts.append(f"Findings: {context['findings_count']} total")

        return ' | '.join(summary_parts)

    def clear_context(self, session_id: str):
        """Clear session context"""
        self.session_contexts.pop(session_id, None)


# Singleton instances
_optimizer = None
_context_manager = None

def get_optimizer() -> ResponseOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = ResponseOptimizer()
    return _optimizer

def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
