"""Install optional hooks in this repository only; no global Git changes."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args]).decode().strip()


email = git('config', '--get', 'user.email')
if not email.endswith('@users.noreply.github.com'):
    raise SystemExit('First configure this repository with your GitHub noreply email.')
hooks = Path(git('rev-parse', '--git-path', 'hooks'))
if not hooks.is_absolute(): hooks = ROOT / hooks
hooks.mkdir(parents=True, exist_ok=True)
contents = {
    'pre-commit': '#!/bin/sh\nexec python scripts/privacy_check.py --staged\n',
    'pre-push': '''#!/bin/sh
git log --all --format='%ae%n%ce' | while IFS= read -r email; do
  case "$email" in
    *@users.noreply.github.com) ;;
    *) echo 'Push blocked: history contains a non-noreply commit email.'; exit 1 ;;
  esac
done
''',
}
for name, content in contents.items():
    target = hooks / name
    if target.exists() and target.read_text(encoding='utf-8') != content:
        raise SystemExit(f'Existing {name} hook found. Merge manually; it was not replaced.')
    target.write_text(content, encoding='utf-8', newline='\n')
    target.chmod(0o755)
git('config', '--local', 'core.hooksPath', str(hooks))
print('Installed repository-local email and content guards.')
