#!/usr/bin/env python3
"""SessionStart hook: add the project's index from the central knowledge base to Claude's context.

Usage: session_start.py [<cache dir>]

Fails open: any problem ends with exit 0 and at most a one-line systemMessage. When GitHub
can't be reached (timeout or network error), the last cached copy of the index is used instead.
"""

import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True  # keep the plugin directory clean
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import kb  # noqa: E402

MAX_LINES = 200
MAX_CHARS = 9000  # hook output is capped at 10,000 characters


def emit(obj):
    print(json.dumps(obj))


def context(repo, name, body, stale):
    lines = body.splitlines()
    cut = len(lines) > MAX_LINES
    lines = lines[:MAX_LINES]
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rsplit("\n", 1)[0]
        cut = True
    head = [
        "# Central knowledge base index",
        "",
        "Index of `%s` in the team's central knowledge base, repository `%s`. "
        "Links in it are relative to `projects/%s/`. Use the kb-search skill to read a page "
        "before you answer from it." % (kb.index_path(name), repo, name),
    ]
    if stale:
        head.append("GitHub could not be reached; this is the last cached copy and may be out of date.")
    if cut:
        head.append("The index was cut. Run the kb-search skill to read the whole index.")
    return "\n".join(head) + "\n\n" + text


def cache_file(cache_dir, repo, name):
    base = cache_dir or os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(tempfile.gettempdir(), "kb-central")
    return os.path.join(base, "cache", repo.replace("/", "--"), name + "-index.md")


def run(argv):
    try:
        json.load(sys.stdin)
    except ValueError:
        pass
    try:
        repo = kb.central_repo()
    except kb.KbError as e:
        return emit({"systemMessage": "kb-central: %s" % e})
    try:
        _, name = kb.project(os.environ.get("CLAUDE_PROJECT_DIR") or None)
    except kb.KbError as e:
        return emit({"systemMessage": "kb-central: %s" % e})

    path = cache_file(argv[1] if len(argv) > 1 else "", repo, name)
    stale = False
    try:
        body = kb.gh_read(kb.index_path(name))
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        except OSError:
            pass
    except kb.KbError as e:
        if not e.transient:
            return emit({"systemMessage": "kb-central: %s" % e})
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
            stale = True
        except OSError:
            return emit({"systemMessage": "kb-central: %s" % e})

    emit({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context(repo, name, body, stale),
        }
    })


if __name__ == "__main__":
    try:
        run(sys.argv)
    except Exception as e:  # a hook must never break the session
        emit({"systemMessage": "kb-central: index not loaded (%s)" % e.__class__.__name__})
    sys.exit(0)
