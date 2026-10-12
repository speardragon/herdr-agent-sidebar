#!/usr/bin/env python3
"""Animate working and blocked Agent markers through Herdr's local socket API."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
# GitHub-installed plugin roots are managed checkouts; keep runtime state outside.
STATE = Path(os.environ.get('HERDR_PLUGIN_STATE_DIR') or ROOT)
STATE.mkdir(parents=True, exist_ok=True)
ENABLED = STATE / 'animations.enabled'
PID = STATE / 'animations.pid'
FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
BLOCKED_FRAMES = '\ue1d0\ue1d0\ue1d1\ue1d2\ue1d3\ue1d2\ue1d1\ue1d0\ue1d0\ue1d0\ue1d0\ue1d0'
INTERVAL = 0.15
MARKS = {'working': '●', 'done': '✓', 'blocked': '?', 'idle': '○', 'unknown': '◌'}
STATUSES = ('working', 'done', 'blocked', 'idle', 'unknown')
SOURCE = 'speardragon.agent-sidebar'
SOCKET = os.environ.get('HERDR_SOCKET_PATH', str(Path.home() / '.config/herdr/herdr.sock'))


class RPCError(RuntimeError):
    pass


def rpc(method: str, params: dict | None = None) -> dict:
    message = {'id': 'ray:sidebar-spinner', 'method': method, 'params': params or {}}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        connection.connect(SOCKET)
        connection.sendall((json.dumps(message, ensure_ascii=False) + '\n').encode())
        with connection.makefile('rb') as stream:
            line = stream.readline(4 * 1024 * 1024)
    if not line:
        raise ConnectionError('Herdr socket closed without a response')
    response = json.loads(line)
    if response.get('error'):
        raise RPCError(str(response['error']))
    return response['result']


def glyph_for(status: str | None, at: float | None = None) -> str:
    if not ENABLED.exists():
        return MARKS.get(status, '◌')
    phase = time.monotonic() if at is None else at
    step = int(phase / INTERVAL)
    if status == 'working':
        return FRAMES[step % len(FRAMES)]
    if status == 'blocked':
        return BLOCKED_FRAMES[step % len(BLOCKED_FRAMES)]
    return MARKS.get(status, '◌')


def tab_tokens(agent: dict, tabs: dict[str, str]) -> dict[str, str]:
    status = agent.get('agent_status')
    if status not in STATUSES:
        status = 'unknown'
    label = tabs.get(agent.get('tab_id'), '')
    return {'agents_tab_' + candidate: label if candidate == status else ''
            for candidate in STATUSES}


def refresh(agents: list[dict], report, at: float | None = None,
            tabs: dict[str, str] | None = None) -> bool:
    """Synchronize markers and exactly one tab-name token per state."""
    animating = False
    for agent in agents:
        status = agent.get('agent_status')
        animating |= status in ('working', 'blocked')
        desired = {'agents_mark': glyph_for(status, at)}
        if tabs is not None:
            desired.update(tab_tokens(agent, tabs))
        current = agent.get('tokens', {})
        changed = {key: value for key, value in desired.items()
                   if current.get(key, '') != value}
        if changed:
            report(agent['pane_id'], changed)
    return animating


def ensure_started() -> None:
    if not ENABLED.exists():
        return
    with (STATE / 'animations.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fcntl.flock(lock, fcntl.LOCK_UN)
        with (STATE / 'animations.log').open('a') as log:
            subprocess.Popen(
                [sys.executable, str(ROOT / 'animations.py'), '--run'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True, close_fds=True,
            )


def report_tokens(pane_id: str, tokens: dict[str, str]) -> None:
    try:
        rpc('pane.report_metadata', {'pane_id': pane_id, 'source': SOURCE,
                                    'tokens': {key: value or None for key, value in tokens.items()}})
    except RPCError as error:
        # A pane may close between agent.list and this display-only update.
        print(f'{pane_id}: {error}', file=sys.stderr, flush=True)


def animate() -> None:
    with (STATE / 'animations.lock').open('a') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        PID.write_text(str(os.getpid()))
        failures = 0
        try:
            while ENABLED.exists():
                started = time.monotonic()
                try:
                    # Event-based group updates and animation share the writer lock.
                    # Always read fresh state after taking it, avoiding stale writes.
                    with (STATE / 'sync.lock').open('a') as lock:
                        fcntl.flock(lock, fcntl.LOCK_EX)
                        agents = rpc('agent.list')['agents']
                        tabs = {t['tab_id']: t['label'] for t in rpc('tab.list')['tabs']}
                        animating = refresh(agents, report_tokens, started, tabs)
                    failures = 0
                except (FileNotFoundError, ConnectionRefusedError):
                    return  # Server startup hooks launch us again on the next start.
                except (OSError, ConnectionError, RPCError, KeyError, ValueError) as error:
                    failures += 1
                    print(f'spinner: {error}', file=sys.stderr, flush=True)
                    if failures >= 3:
                        return
                    animating = False
                delay = INTERVAL if animating else 1.0
                time.sleep(max(0.01, delay - (time.monotonic() - started)))
            # A user-requested stop restores static marks without touching agents.
            try:
                with (STATE / 'sync.lock').open('a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    tabs = {t['tab_id']: t['label'] for t in rpc('tab.list')['tabs']}
                    refresh(rpc('agent.list')['agents'], report_tokens, tabs=tabs)
            except (OSError, ConnectionError, RPCError):
                pass
        finally:
            if PID.exists() and PID.read_text() == str(os.getpid()):
                PID.unlink()


def running() -> bool:
    with (STATE / 'animations.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def set_enabled(enabled: bool) -> None:
    if enabled:
        ENABLED.touch()
        ensure_started()
    else:
        ENABLED.unlink(missing_ok=True)
    until = time.monotonic() + 5
    while running() != enabled:
        if time.monotonic() > until:
            raise RuntimeError('Animation process did not reach the requested state')
        time.sleep(0.05)
    subprocess.run([sys.executable, str(ROOT / 'sync.py')], check=True)


def control() -> None:
    with (STATE / 'animations-control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if '--status' not in sys.argv:
            enabled = '--on' in sys.argv or ('--toggle' in sys.argv and not ENABLED.exists())
            set_enabled(enabled)
            message = 'Agents 애니메이션 켜짐' if enabled else 'Agents 애니메이션 꺼짐'
            subprocess.run([os.environ.get('HERDR_BIN_PATH', 'herdr'), 'notification', 'show',
                            message, '--sound', 'none'], capture_output=True)
        print(json.dumps({'enabled': ENABLED.exists(), 'running': running()}, ensure_ascii=False))


if __name__ == '__main__':
    if '--run' in sys.argv:
        animate()
    else:
        control()
