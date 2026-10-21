"""Offline subprocess and policy-cache regression checks for agent-gate.py."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


def selftest():
    gate = Path(__file__).with_name('agent-gate.py')
    labels = ('CONTEXT', 'REUSE', 'CHANGE', 'GOAL', 'VERIFY')
    spec = '\n'.join(label + ': fixture' for label in labels)
    failures, count = [], 0
    def check(name, condition):
        nonlocal count
        count += 1
        print(('PASS ' if condition else 'FAIL ') + name)
        if not condition:
            failures.append(name)
    with tempfile.TemporaryDirectory(prefix='agent-gate-') as tmp:
        root = Path(tmp)
        policy, decisions, cache = (root / name for name in ('policy.json', 'decisions.jsonl', 'cache.json'))
        policy.write_text(json.dumps({'policy': {'conserve_claude': True}}))
        decisions.write_text('\n'.join(json.dumps({'kind': 'decision', 'id': key, 'decision': value})
            for key, value in [('builder-id', {'builder': {'provider': 'anthropic'}}),
                               ('audit-id', {'auditor': {'provider': 'anthropic'}}),
                               ('other-id', {'builder': {'provider': 'openai'}})]))
        env = dict(os.environ, AGENT_GATE_POLICY_PATH=str(policy), AGENT_GATE_DECISIONS_PATH=str(decisions),
                   AGENT_GATE_CACHE_PATH=str(cache), CLAUDE_CODE_ENTRYPOINT='cli')
        for key in ('HARNESS_HOOKS', 'HARNESS_ALLOW_CLAUDE'):
            env.pop(key, None)
        def run(agent='codex', prompt=spec, tool='Agent', raw=None, **overrides):
            data = {'hook_event_name': 'PreToolUse', 'tool_name': tool,
                    'tool_input': {'prompt': prompt}}
            if agent is not None:
                data['tool_input']['subagent_type'] = agent
            result = subprocess.run([sys.executable, str(gate)], input=raw if raw is not None else json.dumps(data),
                                    capture_output=True, text=True, env=dict(env, **overrides), timeout=10)
            check('process exits silently on stderr', result.returncode == 0 and result.stderr == '')
            if not result.stdout:
                return ''
            output = json.loads(result.stdout)['hookSpecificOutput']
            check('PreToolUse deny protocol', output['hookEventName'] == 'PreToolUse' and
                  output['permissionDecision'] == 'deny')
            return output['permissionDecisionReason']
        for tool in ('Agent', 'Task'):
            check(tool + ' blocks Claude', 'Claude weekly is scarce' in run('claude', tool=tool))
        for agent in ('opus', 'opus48-audit', 'fork', 'general-purpose', 'Explore', 'Plan', None):
            check(str(agent) + ' routing blocked', bool(run(agent)))
        for agent in ('codex', 'codex-audit', 'codex:codex-rescue', 'gemini'):
            check(agent + ' routing allowed', run(agent) == '')
        check('codex-audit has no spec gate', run('codex-audit', '') == '')
        for agent in ('codex', 'claude'):
            for label in labels:
                text = '\n'.join(key + ': fixture' for key in labels if key != label)
                message = run(agent, text, HARNESS_ALLOW_CLAUDE='1')
                check(agent + ' requires ' + label, message.startswith('Missing spec labels: ' + label + '.'))
            for text in ('\n'.join('**'+key+':** fixture' for key in labels),
                         '\n'.join('# '+key+': fixture' for key in labels), spec):
                check(agent + ' accepts labels', run(agent, text, HARNESS_ALLOW_CLAUDE='1') == '')
        check('inline labels insufficient', bool(run(prompt=' '.join(key+':' for key in labels))))
        check('reasoned research exemption', run(prompt='SPEC: n/a — research questions') == '')
        for text in ('SPEC: n/a', 'SPEC: n/a   ', 'SPEC: n/a **', 'SPEC: n/a --'):
            check('empty exemption rejected ' + repr(text), bool(run(prompt=text)))
        for key in ('builder-id', 'audit-id'):
            check(key + ' allows Claude', run('claude', spec + '\nID: ' + key) == '')
        check('inline ID accepted', run('claude', spec+'\nRouter ID: builder-id') == '')
        for key in ('unknown', 'other-id'):
            check(key + ' blocked', bool(run('claude', spec + '\nID: ' + key)))
        check('ID does not waive spec', 'GOAL' in run('claude', 'ID: builder-id'))
        check('escape routing only', 'GOAL' in run('claude', '', HARNESS_ALLOW_CLAUDE='1'))
        check('escape allows complete Claude', run('claude', HARNESS_ALLOW_CLAUDE='1') == '')
        for status in ({'policy': {'conserve_claude': False}}, {}, {'policy': {}}):
            policy.write_text(json.dumps(status))
            check('false/missing policy allows Claude', run('claude') == '')
        for text in ('{bad', '[]', '{"policy": null}', '{"policy":{"conserve_claude":"true"}}'):
            policy.write_text(text)
            check('invalid policy fails open', run('claude') == '')
        policy.write_text('{"policy":{"conserve_claude":true}}')
        for raw in ('{bad', '[]', '{}', '{"hook_event_name":"PreToolUse","tool_name":"Agent","tool_input":null}',
                    '{"hook_event_name":"PreToolUse","tool_name":"Agent","tool_input":{"prompt":4}}'):
            check('invalid payload fails open', run(raw=raw) == '')
        check('unrelated tool ignored', run('claude', tool='Bash') == '')
        check('other event ignored', run(raw='{"hook_event_name":"SubagentStart"}') == '')
        check('missing policy fails open', run('claude', AGENT_GATE_POLICY_PATH=str(root/'missing')) == '')
        check('missing decisions fails open', run('claude', spec+'\nID: x', AGENT_GATE_DECISIONS_PATH=str(root/'missing')) == '')
        decisions.write_text(json.dumps({'kind': 'outcome', 'id': 'outcome-id',
                                        'decision': {'builder': {'provider': 'anthropic'}}}))
        check('outcome ID cannot allow Claude', bool(run('claude', spec+'\nID: outcome-id')))
        decisions.write_text('{bad')
        check('broken decisions fails open', run('claude', spec+'\nID: x') == '')
        check('SDK prefix skips', run('claude', CLAUDE_CODE_ENTRYPOINT='sdk-cli') == '')
        check('SDK on enforces', bool(run('claude', CLAUDE_CODE_ENTRYPOINT='sdk-cli', HARNESS_HOOKS='on')))
        check('off skips', run('claude', HARNESS_HOOKS='off') == '')
        check('off beats SDK opt-in', run('claude', CLAUDE_CODE_ENTRYPOINT='sdk', HARNESS_HOOKS='off') == '')
        module = runpy.run_path(str(gate))
        cache_env = dict(env)
        cache_env.pop('AGENT_GATE_POLICY_PATH')
        cache_env['FMR_HOME'] = str(root)
        with patch.dict(os.environ, cache_env, clear=True), patch('subprocess.run') as call:
            cache.write_text('{"policy":{"conserve_claude":true}}')
            check('fresh cache used', module['policy']() is True and not call.called)
            os.utime(cache, (time.time()-301, time.time()-301))
            call.return_value.stdout = '{"policy":{"conserve_claude":false}}'
            check('expired cache refreshed', module['policy']() is False and call.call_count == 1)
            args, kwargs = call.call_args
            check('fmr command/cwd/5s timeout', args[0] == [str(root/'.venv/bin/python'), '-m', 'fmr', 'status', '--json']
                  and kwargs['cwd'] == root and kwargs['timeout'] == 5 and kwargs['check'] is True)
            check('refresh persists cache', json.loads(cache.read_text())['policy']['conserve_claude'] is False)
            cache.unlink()
            check('absent cache refreshed', module['policy']() is False and call.call_count == 2)
            os.utime(cache, (time.time()-300, time.time()-300))
            call.side_effect = subprocess.TimeoutExpired('fmr', 5)
            with patch('sys.stdin') as stdin, patch('builtins.print') as output, patch.object(sys, 'argv', [str(gate)]):
                stdin.read.return_value = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Agent',
                                                      'tool_input': {'subagent_type': 'claude', 'prompt': spec}})
                # Execute the actual entrypoint's fail-open handler with the mocked timeout.
                runpy.run_path(str(gate), run_name='__main__')
                silent = not output.called
            check('fmr timeout fails open silent', silent and call.call_count == 3)
        cache.write_text('{bad')
        check('bad cache fails open', run('claude', AGENT_GATE_POLICY_PATH='') == '')
    print(f'{count} checks; {len(failures)} failures')
    return bool(failures)
