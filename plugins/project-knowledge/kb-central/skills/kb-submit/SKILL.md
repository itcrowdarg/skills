---
name: kb-submit
description: Sends what was learned in this project to the team's central knowledge base as a GitHub issue in the repository named by KB_CENTRAL_REPO. Use after a non-trivial problem was solved (build, Docker, deploy, dependencies, configuration, services, OS or architecture differences, a non-obvious project behavior), or when the user asks to share something with the team's knowledge base. Always shows the issue and asks before sending.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py *)
---

# Send knowledge to the central knowledge base

The central knowledge base is a private GitHub repository shared by the whole team. You never write to it directly: you open an issue with a fixed format, and a scheduled routine turns valid issues into wiki pages through a pull request that a person reviews.

## What to send

Send problems and facts another developer of this project is likely to need again: setup, build, Docker, deploy, CI, dependency, configuration and local service problems, OS or architecture differences, and project behavior that is not obvious from the code.

Don't send bugs in the code of the current task, tests that fail while a feature is in progress, or one-off mistakes like typos.

If the problem is already in the central index (loaded at session start under "Central knowledge base index"), don't create a duplicate. Offer action `update` with that page's slug as the reference instead.

## Steps

### 1. Check the configuration and the project

Run:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py project
```

If `python3` doesn't exist, run the same command with `python`. It prints `url <project url>` and `name <project name>`. If it prints an error about `KB_CENTRAL_REPO`, show the error to the user and stop. Otherwise read the repository name with `echo "$KB_CENTRAL_REPO"`.

### 2. Draft the fields

| Field | Value |
|---|---|
| Project | The `url` printed in step 1 |
| Category | `knowledge-base` |
| Action | `create` for something new, `update` to correct or extend an existing page, `deprecate` when a page no longer applies |
| Title | One line, at most 120 characters, that says what fails or what it is about. Example: `node-gyp fails building the Docker image on Alpine` |
| Text | Four short sections in this order: **Symptom** (what the developer sees, with the literal error text), **Cause**, **Solution** (exact commands or changes), **How to verify** |
| Proposed scope | `all` if it happens everywhere. Otherwise the environments where it was seen, comma-separated, as `<os>-<arch>`: `macos-arm64`, `macos-x86_64`, `linux-x86_64`, `linux-arm64`, `wsl-x86_64`. Detect the current one with `uname -sm`, and WSL when `/proc/version` contains `microsoft` |
| Reference (optional) | The slug of the existing page, required for `update` and `deprecate`. Empty for `create` |

Write the title and the text in English.

### 3. Redact

Pass the title and the text through the redaction script:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py redact <<'KB_REDACT_END'
<title and text>
KB_REDACT_END
```

It replaces tokens, passwords, connection strings, private keys, IP addresses, internal hosts, emails and home paths. Then read the result yourself and replace what a script can't detect: customer and company names, product names of the client, internal URLs, people's names. Use neutral placeholders such as `<client>` or `<internal-url>`.

### 4. Show the issue and ask

Build the body with exactly these headings, in this order, separated by blank lines. This is how GitHub renders the issue form, and the routine rejects any other shape:

```
### Project

<project url>

### Category

knowledge-base

### Action

<create|update|deprecate>

### Title

<title>

### Text

<text>

### Proposed scope

<scope>

### Reference (optional)

<slug, or _No response_ when empty>
```

Show the user the repository, the title and the full body. Ask whether to send it. **Never create the issue without a clear yes.** If the user asks for changes, apply them, redact again and show it again.

### 5. Create the issue

Write the body to a temporary file outside the project, then create the issue:

```sh
f=$(mktemp) && cat > "$f" <<'KB_ISSUE_END'
<body>
KB_ISSUE_END
gh issue create --repo "$KB_CENTRAL_REPO" --label kb --label kb:pending --title "<title>" --body-file "$f"; rm -f "$f"
```

- If `gh` fails because of a label, run the same command once more without the two `--label` options and tell the user the issue has no labels.
- If `gh` is missing or not authenticated (`gh auth status` fails), don't try to install or log in. Print the title and the body, and give the user `https://github.com/<KB_CENTRAL_REPO>/issues/new` to paste them by hand.

### 6. Report

Give the user the issue URL. Tell them the wiki changes after the next run of the hourly routine and after a person merges its pull request, so the page doesn't appear right away.
