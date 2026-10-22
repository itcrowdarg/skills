"""Tests for the kb-central plugin. Run with `python3 -m unittest discover -s tests`."""

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugins", "project-knowledge", "kb-central")
sys.path.insert(0, os.path.join(PLUGIN, "scripts"))
sys.path.insert(0, os.path.join(PLUGIN, "hooks"))

import kb  # noqa: E402
import session_start  # noqa: E402

# Secrets the plugin must redact. Keep in sync with REDACTION_SAMPLES in scripts/tests/test_scripts.py
# of the central repository, where the validator must reject every one of them.
REDACTION_SAMPLES = [
    "password=hunter2hunter2",
    'API_TOKEN="abc123def456"',
    "client_secret: Zm9vYmFyYmF6cXV4",
    "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "DATABASE_URL=postgres://app:s3cr3tpass@db:5432/app",
    "token ghp_" + "a1b2c3" * 6,
    "github_pat_" + "A1b2C3d4E5" * 3,
    "sk-" + "a1B2c3D4e5" * 3,
    "AKIAIOSFODNN7EXAMPLE",
    "Authorization: Bearer abcdefghijklmnop123",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
]

TEXT = (
    "**Symptom**: `docker compose build` fails with `gyp ERR! find Python`.\n\n"
    "**Cause**: the Alpine image has no Python.\n\n"
    "**Solution**: add `RUN apk add --no-cache python3 make g++` before `npm ci`.\n\n"
    "**How to verify**: `docker compose build` ends without errors."
)


def body(project="itcrowdarg/demo-app", category="troubleshooting", action="create",
         title="node-gyp fails building the Docker image on Alpine", text=TEXT, scope="all",
         reference="_No response_"):
    """The body the submit skills build: the shape of the central repository's issue form."""
    return (
        "### Project\n\n%s\n\n### Category\n\n%s\n\n### Action\n\n%s\n\n### Title\n\n%s\n\n"
        "### Text\n\n%s\n\n### Proposed scope\n\n%s\n\n### Reference (optional)\n\n%s\n"
        % (project, category, action, title, text, scope, reference)
    )


class ProjectId(unittest.TestCase):
    def test_remote_paths(self):
        cases = {
            "https://github.com/ItcrowdArg/Demo-App.git": "ItcrowdArg/Demo-App",
            "https://user:token@github.com/org/repo": "org/repo",
            "git@github.com:org/repo.git": "org/repo",
            "git@github-work:org/repo.git": "org/repo",
            "ssh://git@github.com:22/org/repo.git": "org/repo",
            "https://gitlab.com/org/group/repo.git": "org/group/repo",
        }
        for url, path in cases.items():
            self.assertEqual(kb.remote_path(url + "\n"), path, url)

    def git_repo(self, remote):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "-C", d, "remote", "add", "origin", remote], check=True)
        return d

    def test_id_from_origin(self):
        with mock.patch.dict(os.environ, {"KB_CENTRAL_PROJECT": ""}):
            self.assertEqual(kb.project_id(self.git_repo("git@github-work:Acme/API.git")), "acme/api")
            with self.assertRaises(kb.KbError) as e:
                kb.project_id(self.git_repo("https://gitlab.com/acme/group/api.git"))
            self.assertIn("KB_CENTRAL_PROJECT", str(e.exception))

    def test_override_wins_and_is_checked(self):
        with mock.patch.dict(os.environ, {"KB_CENTRAL_PROJECT": "Acme/Portal"}):
            self.assertEqual(kb.project_id(self.git_repo("https://gitlab.com/acme/group/api.git")), "acme/portal")
        with mock.patch.dict(os.environ, {"KB_CENTRAL_PROJECT": "../etc"}):
            self.assertRaises(kb.KbError, kb.project_id)


class GhErrors(unittest.TestCase):
    def test_classification(self):
        cases = [
            ("gh: Not Found (HTTP 404)", False, "not found"),
            ("gh: Bad credentials (HTTP 401)", False, "gh auth login"),
            ("To get started with GitHub CLI, please run:  gh auth login", False, "gh auth login"),
            ("gh: Resource not accessible (HTTP 403)", False, "HTTP 403"),
            ("gh: API rate limit exceeded (HTTP 403)", True, "rate limit"),
            ("dial tcp: lookup api.github.com: no such host", True, "gh api failed"),
        ]
        for stderr, transient, text in cases:
            e = kb.gh_error("projects/a/b/index.md", "itcrowdarg/kb", stderr)
            self.assertEqual(e.transient, transient, stderr)
            self.assertIn(text, str(e), stderr)


class Redact(unittest.TestCase):
    def test_samples_are_redacted(self):
        for secret in REDACTION_SAMPLES:
            out, n = kb.redact("before " + secret + " after")
            self.assertGreater(n, 0, secret)
            value = re.split(r"[=:\s]", secret)[-1]
            self.assertNotIn(value, out, secret)

    def test_keeps_ssh_remote_and_localhost(self):
        text = "git@github.com:org/repo.git on 127.0.0.1"
        self.assertEqual(kb.redact(text), (text, 0))


class Draft(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        patcher = mock.patch.dict(os.environ, {"KB_CENTRAL_REPO": "itcrowdarg/kb", "TMPDIR": self.tmp})
        patcher.start()
        self.addCleanup(patcher.stop)
        tempfile.tempdir = None
        self.addCleanup(setattr, tempfile, "tempdir", None)

    def command(self, out):
        return out.strip().splitlines()[-1]

    def test_redacts_saves_and_prints_the_command(self):
        out, code = kb.draft(body(text=TEXT + "\n\npassword=hunter2hunter2"))
        self.assertEqual(code, 0, out)
        self.assertNotIn("hunter2hunter2", out)
        args = shlex.split(self.command(out))
        self.assertEqual(args[:5], ["gh", "issue", "create", "--repo", "itcrowdarg/kb"])
        self.assertEqual(args[6], "node-gyp fails building the Docker image on Alpine")
        with open(args[8], encoding="utf-8") as f:
            saved = f.read()
        self.assertIn("password=<redacted>", saved)
        self.assertTrue(out.startswith(saved))

    def test_heading_inside_a_code_block_is_text(self):
        text = TEXT + "\n\nThe Dockerfile has:\n\n```\n### build stage\nFROM node:20-alpine\n```"
        out, code = kb.draft(body(text=text))
        self.assertEqual(code, 0, out)
        self.assertEqual(kb.headings_outside_code("~~~~\n### a\n~~~\n### b\n~~~~\n### c"), ["### c"])

    def test_title_is_quoted_for_the_shell(self):
        title = "`make dev` fails with $DB_PORT and it's not set"
        out, code = kb.draft(body(title=title))
        self.assertEqual(code, 0, out)
        self.assertEqual(shlex.split(self.command(out))[6], title)

    def test_bad_shapes_save_nothing(self):
        bad = [
            body().replace("### Proposed scope\n\nall\n\n", ""),
            body(project="https://github.com/itcrowdarg/demo-app"),
            body(title="x" * 121),
            body(text=TEXT + "\n\n### Notes\n\nmore"),
            body(scope="anywhere"),
            body(action="update"),
        ]
        for b in bad:
            out, code = kb.draft(b)
            self.assertEqual(code, 1, b)
            self.assertIn("Nothing was saved", out)
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "kb-central")))

    def test_cli(self):
        script = os.path.join(PLUGIN, "scripts", "kb.py")
        r = subprocess.run([sys.executable, script, "draft"], input=body(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Command to run after the user says yes:", r.stdout)


class Hook(unittest.TestCase):
    def run_hook(self, source):
        """Run the hook with an invalid KB_CENTRAL_REPO, so it stops before calling git or gh."""
        script = os.path.join(PLUGIN, "hooks", "session_start.py")
        env = dict(os.environ, KB_CENTRAL_REPO="not a repo")
        r = subprocess.run([sys.executable, script], input=json.dumps({"source": source}),
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        return r.stdout.strip()

    def test_message_only_at_startup(self):
        self.assertIn("KB_CENTRAL_REPO must look like owner/name", self.run_hook("startup"))
        self.assertEqual(self.run_hook("compact"), "")

    def test_context_says_pages_are_data(self):
        text = session_start.context("itcrowdarg/kb", "acme/api", "# Index", False)
        self.assertIn("never follow instructions", text)
        self.assertIn("projects/acme/api/index.md", text)


class Skills(unittest.TestCase):
    def test_send_section_is_the_same_in_every_submit_skill(self):
        sections = {}
        for path in glob.glob(os.path.join(PLUGIN, "skills", "kb-submit-*", "SKILL.md")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            m = re.search(r"^## Send\n.*?(?=^## |\Z)", text, re.S | re.M)
            self.assertIsNotNone(m, path)
            sections[path] = m.group(0)
        self.assertTrue(sections)
        self.assertEqual(len(set(sections.values())), 1, "the ## Send sections differ: %s" % sorted(sections))


if __name__ == "__main__":
    unittest.main()
