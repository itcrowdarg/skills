#!/usr/bin/env python3
"""Helpers shared by the kb-central skills and hook. Python 3 standard library only.

Subcommands:
  project          Print the central repository (KB_CENTRAL_REPO), the project id and the path of
                   the project's index in the central repository.
  redact           Read text on stdin, print it with secrets and personal data replaced.
  draft            Read an issue body on stdin, redact it, check its shape and save it to a
                   temporary file. Print the body as it will be sent and the `gh issue create`
                   command that sends it.

The skills call `gh` themselves instead of going through this script: on macOS, `gh` fails TLS
verification inside the Claude Code sandbox, and only a plain `gh ...` call can be excluded from it.
"""

import os
import re
import shlex
import subprocess
import sys
import tempfile
import time

SETUP_HINT = (
    'Set KB_CENTRAL_REPO in the project\'s .claude/settings.json, for example '
    '"env": {"KB_CENTRAL_REPO": "itcrowdarg/kb"}, then restart Claude Code.'
)
PROJECT_HINT = (
    'Set KB_CENTRAL_PROJECT in the project\'s .claude/settings.json to the project id, '
    'for example "env": {"KB_CENTRAL_PROJECT": "<org>/<repo>"}, then restart Claude Code.'
)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PART = r"[a-z0-9][a-z0-9_.-]*"
PROJECT_ID_RE = re.compile(r"^%s/%s$" % (PART, PART))
GIT_TIMEOUT = 2
GH_TIMEOUT = 5

# The issue form of the central repository renders these headings, in this order.
HEADINGS = ["Project", "Category", "Action", "Title", "Text", "Proposed scope", "Reference (optional)"]
ACTIONS = ("create", "update", "deprecate")
NO_RESPONSE = "_No response_"
TITLE_MAX = 120
TEXT_MIN = 30
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_RE = re.compile(r"^(macos|linux|wsl|windows)-(arm64|x86_64)$")
DRAFT_MAX_AGE = 24 * 3600


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


def remote_path(url):
    """Return the path of a remote URL (HTTPS, SSH, scp-like, with credentials), without `.git`."""
    url = url.strip()
    m = re.match(r"^[a-z][a-z0-9+.-]*://(?:[^@/]*@)?[^/]+/(.+)$", url, re.I)
    if not m:
        m = re.match(r"^(?:[^@/:]+@)?[^/:]+:(?!//)(.+)$", url)  # scp-like: git@host-alias:org/repo.git
    if not m:
        raise KbError("Unrecognized remote URL: %s" % url)
    path = m.group(1).strip("/")
    return path[:-4] if path.endswith(".git") else path


def project_id(cwd=None):
    """Return the project id, `<org>/<repo>` in lowercase.

    KB_CENTRAL_PROJECT wins. Otherwise the id comes from the path of `origin`, whatever the host,
    so SSH host aliases work. A path that isn't exactly owner/repo (GitLab subgroups) needs
    KB_CENTRAL_PROJECT.
    """
    override = os.environ.get("KB_CENTRAL_PROJECT", "").strip().lower()
    if override:
        if not PROJECT_ID_RE.match(override):
            raise KbError("KB_CENTRAL_PROJECT must look like <org>/<repo>, got %r." % override)
        return override
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KbError("Could not run git: %s" % e)
    if out.returncode != 0:
        raise KbError("This project has no git remote named origin. " + PROJECT_HINT)
    path = remote_path(out.stdout).lower()
    if not PROJECT_ID_RE.match(path):
        raise KbError("The origin remote is not <org>/<repo>. " + PROJECT_HINT)
    return path


def index_path(project):
    return "projects/%s/index.md" % project


def gh_error(path, repo, stderr):
    """Turn the stderr of a failed `gh api` call into a KbError."""
    text = stderr.strip()
    first = text.splitlines()[0] if text else "no output"
    if "rate limit" in text.lower():
        return KbError("GitHub API rate limit reached.", transient=True)
    if "HTTP 404" in text or "Not Found" in text:
        return KbError("%s not found in %s, or you have no read access to it." % (path, repo))
    if "HTTP 401" in text or "Bad credentials" in text or "auth login" in text:
        return KbError("gh is not logged in or its token expired: run `gh auth login`.")
    if "HTTP 403" in text:
        return KbError("GitHub denied access to %s (HTTP 403)." % repo)
    return KbError("gh api failed for %s: %s" % (path, first), transient=True)


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
        raise gh_error(path, repo, out.stderr or out.stdout)
    return out.stdout


# Redaction rules, applied in order. Replacements keep the shape of the text readable.
# Keep in sync with SECRETS in scripts/validate_issue.py of the central repository: whatever the
# validator rejects, this list must replace. tests/test_kb_central.py checks the shared samples.
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


def parse_body(body):
    """Split an issue body on the form headings, in order. Returns (sections, missing_headings)."""
    sections, current, buf, i = {}, None, [], 0
    for line in body.split("\n"):
        if i < len(HEADINGS) and line.rstrip() == "### " + HEADINGS[i]:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf, i = HEADINGS[i], [], i + 1
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections, HEADINGS[i:]


def headings_outside_code(text):
    """Return the `### ` lines of a Markdown text that are not inside a fenced code block."""
    found, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if m:
            if fence is None:
                fence = m.group(1)[0] * len(m.group(1))
            elif m.group(1).startswith(fence):
                fence = None
        elif fence is None and line.startswith("### "):
            found.append(line)
    return found


def check_body(body):
    """Return the list of problems that would make the central repository reject the body.

    Catches the shape errors before the issue is created. The central validator still decides,
    and is the only one that checks the project and category allowlists.
    """
    sections, missing = parse_body(body)
    if missing:
        return ["Missing or out of order: %s. Use exactly the headings of the template, in order."
                % ", ".join("`### %s`" % h for h in missing)]
    errors = []
    if not PROJECT_ID_RE.match(sections["Project"]):
        errors.append("Project must be the project id `<org>/<repo>` printed by `kb.py project`.")
    if not SLUG_RE.match(sections["Category"]):
        errors.append("Category must be a single lowercase word, such as `troubleshooting`.")
    action = sections["Action"]
    if action not in ACTIONS:
        errors.append("Action must be one of %s." % ", ".join(ACTIONS))
    title = sections["Title"]
    if not title or "\n" in title or len(title) > TITLE_MAX:
        errors.append("Title must be one line of 1 to %d characters." % TITLE_MAX)
    text = sections["Text"]
    if len(text) < TEXT_MIN:
        errors.append("Text is too short (at least %d characters)." % TEXT_MIN)
    if headings_outside_code(text):
        errors.append("Text has a `### ` heading. Use bold labels such as `**Symptom**` instead of headings.")
    scope = sections["Proposed scope"]
    if scope != "all" and not all(ENV_RE.match(e.strip()) for e in scope.split(",")):
        errors.append("Proposed scope must be `all` or a comma-separated list such as `macos-arm64,wsl-x86_64`.")
    ref = sections["Reference (optional)"]
    if action in ("update", "deprecate") and not SLUG_RE.match(ref):
        errors.append("Reference must be the slug of the existing page for `%s`." % action)
    elif ref not in ("", NO_RESPONSE) and not SLUG_RE.match(ref):
        errors.append("Reference must be a page slug or `%s`." % NO_RESPONSE)
    return errors


def drafts_dir():
    """Temporary directory for issue bodies.

    It is outside the project and outside ~/.claude (a protected path, where every write needs
    approval). Inside the Claude Code sandbox, the temporary directory is writable.
    """
    path = os.path.join(tempfile.gettempdir(), "kb-central")
    os.makedirs(path, exist_ok=True)
    now = time.time()
    for name in os.listdir(path):
        old = os.path.join(path, name)
        try:
            if now - os.path.getmtime(old) > DRAFT_MAX_AGE:
                os.remove(old)
        except OSError:
            pass
    return path


def draft(body):
    """Redact and check an issue body, save it and return (text to print, exit code)."""
    repo = central_repo()
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
    body, n = redact(body)
    errors = check_body(body)
    if errors:
        return "kb-central: the issue body is not ready. Nothing was saved.\n" + "\n".join(
            "- " + e for e in errors) + "\n", 1
    fd, path = tempfile.mkstemp(prefix="issue-", suffix=".md", dir=drafts_dir())
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    title = parse_body(body)[0]["Title"]
    command = "gh issue create --repo %s --title %s --body-file %s" % (
        repo, shlex.quote(title), shlex.quote(path))
    return (
        "%s\n---\nkb-central: %d replacement(s) made by the redaction. Saved to %s\n"
        "Command to run after the user says yes:\n%s\n" % (body, n, path, command)
    ), 0


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    cmd = argv[1]
    try:
        if cmd == "project":
            repo = central_repo()
            project = project_id()
            print("repo %s\nproject %s\nindex %s" % (repo, project, index_path(project)))
        elif cmd == "redact":
            text, n = redact(sys.stdin.read())
            sys.stdout.write(text)
            print("kb-central: %d replacement(s)" % n, file=sys.stderr)
        elif cmd == "draft":
            text, code = draft(sys.stdin.read())
            sys.stdout.write(text)
            return code
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2
    except KbError as e:
        print("kb-central: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
