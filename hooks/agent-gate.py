#!/usr/bin/env python3
"""Blocking Agent/Task routing and builder-spec gate; errors silently fail open."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

CLAUDE = {'claude', 'opus', 'opus48-audit', 'fork', 'general-purpose', 'Explore', 'Plan', ''}
LABELS = ('CONTEXT', 'REUSE', 'CHANGE', 'GOAL', 'VERIFY')


def policy():
    fixture = os.environ.get('AGENT_GATE_POLICY_PATH')
    if fixture:
        status = json.loads(Path(fixture).read_text())
    else:
        cache = Path(os.environ.get('AGENT_GATE_CACHE_PATH',
                         str(Path.home() / '.cache/awesome-harness/agent-policy.json')))
        if cache.exists() and 0 <= time.time() - cache.stat().st_mtime < 300:
            status = json.loads(cache.read_text())
        else:
            home = Path(os.environ.get('FMR_HOME', str(Path.home() / 'Downloads/free-model-router')))
            result = subprocess.run([str(home / '.venv/bin/python'), '-m', 'fmr', 'status', '--json'],
                                    cwd=home, capture_output=True, text=True, timeout=5, check=True)
            status = json.loads(result.stdout)
            validate_policy(status)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(status))
    return validate_policy(status)


def validate_policy(status):
    if not isinstance(status, dict):
        raise ValueError('invalid fmr status')
    value = status.get('policy', {})
    if not isinstance(value, dict) or ('conserve_claude' in value and
                                       not isinstance(value['conserve_claude'], bool)):
        raise ValueError('invalid fmr policy')
    return value.get('conserve_claude', False)


def approved(prompt):
    ids = set(re.findall(r'\bID:\s*([^\s*]+)', prompt))
    if not ids:
        return False
    path = Path(os.environ.get('AGENT_GATE_DECISIONS_PATH',
                    str(Path.home() / '.local/state/free-model-router/decisions.jsonl')))
    for line in path.read_text().splitlines():
        item = json.loads(line)
        if item.get('kind') == 'decision' and item.get('id') in ids:
            decision = item['decision']
            if any(decision.get(role, {}).get('provider') == 'anthropic'
                   for role in ('builder', 'auditor')):
                return True
    return False


def reason(payload):
    if payload.get('hook_event_name') != 'PreToolUse' or payload.get('tool_name') not in ('Agent', 'Task'):
        return ''
    data = payload['tool_input']
    agent, prompt = data.get('subagent_type', ''), data.get('prompt', '')
    if not isinstance(agent, str) or not isinstance(prompt, str):
        raise ValueError('invalid Agent input')
    if agent in CLAUDE and os.environ.get('HARNESS_ALLOW_CLAUDE') != '1' and policy() and not approved(prompt):
        return ('Claude weekly is scarce; use `codex` (builds) / `codex-audit` (audits) '
                'or run route-model.sh and pass its ID: <fmr id>.')
    if agent in ('codex', 'claude'):
        exemption = re.search(r'(?m)^\s*(?:#+\s*|\*\*)?SPEC:\s*n/a\b([^\n]*)', prompt)
        if exemption and re.search(r'\w', exemption[1].replace('**', '')):
            return ''
        missing = [label for label in LABELS if not re.search(
            r'(?m)^\s*(?:#+\s*|\*\*)?' + label + r'(?:\*\*)?\s*:', prompt)]
        if missing:
            return 'Missing spec labels: ' + ', '.join(missing) + '. Use SPEC: n/a with a reason for research/questions.'
    return ''


def main():
    mode = os.environ.get('HARNESS_HOOKS')
    if mode == 'off' or (os.environ.get('CLAUDE_CODE_ENTRYPOINT', '').startswith('sdk') and mode != 'on'):
        return
    message = reason(json.load(sys.stdin))
    if message:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
              'permissionDecision': 'deny', 'permissionDecisionReason': message}}))


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        from agent_gate_selftest import selftest
        sys.exit(selftest())
    try:
        main()
    except Exception:
        pass  # Required fail-open: malformed input, unavailable fmr/cache, or any crash.
