---
name: kb-submit-troubleshooting
description: Sends a solved problem of this project to the team's central knowledge base as a GitHub issue in the repository named by KB_CENTRAL_REPO. Use after a non-trivial problem was solved (build, Docker, deploy, dependencies, configuration, local services, OS or architecture differences, a non-obvious project behavior that made something fail), or when the user asks to share a problem and its solution with the team's knowledge base. Always shows the issue and asks before sending.
allowed-tools:
  - Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py *)
  - Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py *)
---

# Send a solved problem to the central knowledge base

The central knowledge base is a private GitHub repository shared by the whole team. You never write to it directly: you open an issue with a fixed format, and a routine in that repository turns valid issues into wiki pages through a pull request that a person reviews.

This skill sends the category `troubleshooting`.

## What to send

Send problems another developer of this project is likely to hit again: setup, build, Docker, deploy, CI, dependency, configuration and local service problems, problems that only happen on one OS or architecture, and project behavior that is not obvious from the code and makes something fail.

Don't send bugs in the code of the current task, tests that fail while a feature is in progress, or one-off mistakes like typos.

If the problem is already in the central index (loaded at session start under "Central knowledge base index"), don't create a duplicate. Offer action `update` with that page's slug (the file name of its link, without `.md`) as the reference instead.

## Fields

| Field | Value |
|---|---|
| Project | The `project` printed by `kb.py project` |
| Category | `troubleshooting` |
| Action | `create` for something new, `update` to correct or extend an existing page, `deprecate` when a page no longer applies |
| Title | One line, at most 120 characters, that says what fails. Example: `node-gyp fails building the Docker image on Alpine` |
| Text | Four parts in this order, each starting with a bold label: **Symptom** (what the developer sees, with the literal error text), **Cause**, **Solution** (exact commands or changes), **How to verify**. Never use `###` headings in the text |
| Proposed scope | `all` if it happens everywhere. Otherwise the environments where it was seen, comma-separated, as `<os>-<arch>`: `macos-arm64`, `macos-x86_64`, `linux-x86_64`, `linux-arm64`, `wsl-x86_64`. Detect the current one with `uname -sm`, and WSL when `/proc/version` contains `microsoft` |
| Reference (optional) | The slug of the existing page, required for `update` and `deprecate`. `_No response_` for `create` |

Write the title and the text in English.

## Send

These steps are the same in every kb-submit skill.

1. **Check the configuration and the project.** Run:

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py project
   ```

   If `python3` doesn't exist, use `python` in this step and in step 3. It prints `repo <owner/name>` (the central repository) and `project <org>/<repo>` (the project id). If it prints an error, show it to the user and stop.

2. **Build the body.** Use exactly these headings, in this order, separated by blank lines. This is how GitHub renders the issue form, and the central repository rejects any other shape:

   ```
   ### Project

   <project id>

   ### Category

   <category>

   ### Action

   <create|update|deprecate>

   ### Title

   <title>

   ### Text

   <text>

   ### Proposed scope

   <scope>

   ### Reference (optional)

   <slug, or _No response_>
   ```

   Before you go on, replace what a script can't detect: customer and company names, product names of the client, internal URLs and people's names. Use neutral placeholders such as `<client>` or `<internal-url>`.

3. **Draft it.** Pass the body to the draft script:

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py draft <<'KB_DRAFT_END'
   <body>
   KB_DRAFT_END
   ```

   It replaces tokens, passwords, connection strings, private keys, IP addresses, internal hosts, emails and home paths. Then it checks the shape and saves the body to a temporary file. It prints the body as it will be sent, the file, and the `gh issue create` command that sends it. If it prints problems instead, fix the body and run it again.

4. **Show it and ask.** Show the user the central repository and the body exactly as the script printed it, without rewriting it. Ask whether to send it. **Never create the issue without a clear yes.** If the user asks for changes, apply them to the body and go back to step 3.

5. **Create the issue.** After the yes, run the command the script printed, copied exactly, as a single command. It looks like this:

   ```sh
   gh issue create --repo <owner/name> --title '<title>' --body-file <file>
   ```

   A plain `gh` call is what a developer can exclude from the Claude Code sandbox (`"excludedCommands": ["gh *"]`). If `gh` fails with `x509` or `failed to verify certificate`, it ran inside the sandbox: tell the user to add `gh *` to `sandbox.excludedCommands` in `~/.claude/settings.json`, and give them the fallback below.

   If `gh` is missing or not authenticated (`gh auth status` fails), don't try to install or log in. Give the user the file path and `https://github.com/<owner/name>/issues/new/choose` to open the issue by hand with the form of the category.

6. **Report.** Give the user the issue URL. Tell them the wiki changes only after the knowledge base routine processes the issue and a person merges its pull request, so the page doesn't appear right away.
