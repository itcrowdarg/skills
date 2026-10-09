#!/usr/bin/env python3
"""Helpers shared by the kb-central skills and hook. Python 3 standard library only.

Subcommands:
  project          Print the central repository (KB_CENTRAL_REPO), the project URL and the project
                   name, the last two from `git remote get-url origin`.
  redact           Read text on stdin, print it with secrets and personal data replaced.

The skills call `gh` themselves instead of going through this script: on macOS, `gh` fails TLS
verification inside the Claude Code sandbox, and only a plain `gh ...` call can be excluded from it.
"""

import os
import re
import subprocess
import sys

SETUP_HINT = (
    'Set KB_CENTRAL_REPO in the project\'s .claude/settings.json, for example '
    '"env": {"KB_CENTRAL_REPO": "itcrowdarg/kb"}, then restart Claude Code.'
)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GH_TIMEOUT = 5


class KbError(Exception):
    """transient=True when GitHub could not be reached, as opposed to a definite answer like 404."""

    def __init__(self, message, transient=False):
        super().__init__(message)
        self.transient = transient


def central_repo():
    repo = os.environ.get("KB_CENTRAL_REPO", "").strip()
    if not repo:
        raise KbError("KB_CENTRAL_REPO is not set. " + SETUP_HINT)
    if not REPO_RE.match(repo):
        raise KbError("KB_CENTRAL_REPO must look like owner/name, got %r." % repo)
    return repo


def normalize_remote(url):
    """Turn any GitHub remote URL (HTTPS, SSH, with credentials) into https://github.com/<org>/<repo>."""
    url = url.strip()
    m = re.match(r"^[\w.-]+@([\w.-]+):(.+)$", url)  # scp-like SSH: git@github.com:org/repo.git
    if m:
        host, path = m.group(1), m.group(2)
    else:
        m = re.match(r"^[a-z+]+://(?:[^@/]*@)?([^/:]+)(?::\d+)?/(.+)$", url)
        if not m:
            raise KbError("Unrecognized remote URL: %s" % url)
        host, path = m.group(1), m.group(2)
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise KbError("Remote URL is not owner/repo: %s" % url)
    return "https://%s/%s/%s" % (host.lower(), parts[0], parts[1])


def project(cwd=None):
    """Return (url, name) of the project in cwd. The name is the repository name in lowercase."""
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True, timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KbError("Could not run git: %s" % e)
    if out.returncode != 0:
        raise KbError("This project has no git remote named origin.")
    url = normalize_remote(out.stdout)
    return url, url.rsplit("/", 1)[1].lower()


def gh_read(path):
    """Return the raw content of one file of the central repository, through `gh api`."""
    repo = central_repo()
    if path.startswith("/") or ".." in path.split("/"):
        raise KbError("Invalid path: %s" % path)
    cmd = [
        "gh", "api", "repos/%s/contents/%s" % (repo, path),
        "-H", "Accept: application/vnd.github.raw",
    ]
    env = dict(os.environ, GH_PROMPT_DISABLED="1")
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=GH_TIMEOUT,
            stdin=subprocess.DEVNULL, env=env,
        )
    except FileNotFoundError:
        raise KbError("GitHub CLI (gh) is not installed. Install it and run `gh auth login`.")
    except subprocess.TimeoutExpired:
        raise KbError("GitHub did not answer within %d s." % GH_TIMEOUT, transient=True)
    if out.returncode != 0:
        err = (out.stderr or out.stdout).strip().splitlines()
        detail = err[0] if err else "exit code %d" % out.returncode
        if "404" in detail or "Not Found" in detail:
            raise KbError("%s not found in %s, or you have no read access to it." % (path, repo))
        raise KbError("gh api failed for %s: %s" % (path, detail), transient=True)
    return out.stdout


def index_path(name):
    return "projects/%s/index.md" % name


# Redaction rules, applied in order. Replacements keep the shape of the text readable.
REDACTIONS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "<redacted-private-key>"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"), "<redacted-token>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<redacted-token>"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "<redacted-token>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<redacted-token>"),
    (re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"), "<redacted-token>"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "<redacted-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "<redacted-token>"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 <redacted>"),
    # scheme://user:password@host/... (database URLs, AMQP, Redis, HTTP with credentials)
    (re.compile(r"\b([a-z][a-z0-9+.-]*)://[^\s/@:]+:[^\s/@]+@[^\s'\"]+", re.I),
     r"\1://<redacted-connection-string>"),
    # key=value or key: value where the key names a secret
    (re.compile(
        r"(?i)\b([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
        r"private[_-]?key|client[_-]?secret|credentials?)[A-Za-z0-9_.-]*)"
        r"(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"),
     r"\1\2<redacted>"),
    (re.compile(r"(?<![\w.@-])(?!git@)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<email>"),
    (re.compile(r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip>"),
    (re.compile(r"\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:internal|intranet|corp|lan|local)\b", re.I),
     "<internal-host>"),
    (re.compile(r"/Users/[^/\s]+"), "~"),
    (re.compile(r"/home/[^/\s]+"), "~"),
    (re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+"), "~"),
]


def redact(text):
    """Return (redacted_text, number_of_replacements)."""
    total = 0
    for pattern, repl in REDACTIONS:
        text, n = pattern.subn(repl, text)
        total += n
    return text, total


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    cmd = argv[1]
    try:
        if cmd == "project":
            repo = central_repo()
            url, name = project()
            print("repo %s\nurl %s\nname %s" % (repo, url, name))
        elif cmd == "redact":
            text, n = redact(sys.stdin.read())
            sys.stdout.write(text)
            print("kb-central: %d replacement(s)" % n, file=sys.stderr)
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2
    except KbError as e:
        print("kb-central: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
