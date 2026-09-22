"""Heuristic prepublication guard over Git files, not a complete secret scanner."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def email_allowed(value):
    domain = value.lower().rsplit('@', 1)[-1]
    return domain == 'users.noreply.github.com' or domain.endswith(('.invalid', '.example')) or domain in {'example.com', 'example.org', 'example.net'}


def main():
    staged = '--staged' in sys.argv
    raw_paths = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z') if staged else git('ls-files', '-z')
    findings = []
    for raw in raw_paths.split(b'\0'):
        if not raw:
            continue
        name = raw.decode('utf-8')
        path = Path(name)
        if path.name in {'.env', 'secrets.toml', 'id_rsa', 'id_ed25519'} or any(part in {'.venv', 'uploads', 'models', 'data', '__pycache__'} for part in path.parts):
            findings.append((name, 'private/runtime file'))
        data = git('show', ':' + name) if staged else (ROOT / path).read_bytes()
        patterns = {
            'credential-like value': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})\b',
            'private key': rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
            'personal machine path': rb'(?i)([A-Z]:[/\\]+Users[/\\]+[^/\\\s]+|/(?:home|Users)/[^/\s]+/)',
        }
        for label, pattern in patterns.items():
            if re.search(pattern, data): findings.append((name, label))
        for match in re.findall(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', data):
            if not email_allowed(match.decode('ascii')): findings.append((name, 'non-placeholder email'))
    if staged:
        for kind in ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT'):
            match = re.search(r'<([^>]+)>', git('var', kind).decode())
            if not match or not match[1].endswith('@users.noreply.github.com'):
                findings.append(('commit identity', 'configure a GitHub noreply email'))
    for filename, reason in findings:
        print(f'{filename}: {reason}')
    print(f'Privacy guard: {len(findings)} finding(s). Manual review is still required.')
    return bool(findings)


if __name__ == '__main__':
    raise SystemExit(main())
