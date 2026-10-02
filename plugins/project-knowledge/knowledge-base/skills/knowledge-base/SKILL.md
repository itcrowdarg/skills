---
name: knowledge-base
description: Project knowledge base of recurring environment problems and their solutions, stored in `.knowledge-base/` at the repository root. Use when a command fails or the user reports or pastes an error (build, Docker, deploy, dependencies, configuration, services, OS or architecture differences), to check whether the problem is already documented. Also use after a non-trivial environment problem was solved, to offer saving it for the rest of the team.
---

# Knowledge base

The knowledge base stores problems that another developer of this project is likely to hit again: a broken Docker build, a deploy that fails after months, a missing environment variable, a dependency that does not compile on one OS. Each problem is one Markdown file, committed with the project, so the whole team shares it.

## What belongs in it

Save:

- Setup, build, Docker, deploy, CI, dependency, configuration and local service problems.
- Problems that only happen on one OS or architecture (macOS, Linux, WSL, arm64, x86_64).
- Anything where the cause was not obvious from the error message.

Do not save:

- Bugs in the code being written as part of the current task.
- Tests that fail while a feature is in progress.
- Typos, wrong paths or other one-off mistakes.

## Layout

```
.knowledge-base/
├── INDEX.md
└── <category>/<slug>.md
```

- `<category>`: a short lowercase noun for the area of the problem. Choose it yourself based on the project. Examples: `docker`, `deploy`, `database`, `dependencies`, `env`, `ci`. Reuse an existing category before creating a new one.
- `<slug>`: kebab-case `<what-fails>-<context>`, at most six words. Example: `node-gyp-missing-python-alpine`.
- `INDEX.md`: one line per entry, grouped by category, sorted by slug:

  ```markdown
  ## docker

  - [node-gyp fails building the image on Alpine](docker/node-gyp-missing-python-alpine.md): `docker compose up --build` fails installing npm dependencies
  ```

## Look up a problem

Do this as soon as a command fails or the user shows an error, before investigating on your own.

1. If `.knowledge-base/` does not exist, skip the lookup.
2. Pick the most distinctive fragment of the error: an error code, a library name, a fixed part of the message. Leave out paths, line numbers, timestamps and IDs.
3. Search it: `grep -ril -- "<fragment>" .knowledge-base/`. If nothing matches, read `.knowledge-base/INDEX.md` and look for a similar symptom.
4. If an entry matches, read it and tell the user in one line: `Known issue: .knowledge-base/<category>/<slug>.md`. Then apply or suggest its solution. Do not ask whether to save it.
5. Compare the entry's `environments` with the current one (see "Detect the environment"). If the problem happened in an environment that is not listed, ask in one line whether to add it, and update `environments` and `updated` after a yes.

## Save a problem

Do this after a problem that belongs in the knowledge base is solved, or when the user asks for it.

1. Search first, as in "Look up a problem". If an entry already covers it, update that entry instead of creating a new one.
2. Ask the user in one line, with the path you plan to use:
   `This looks like a problem other developers can hit. Save it to .knowledge-base/<category>/<slug>.md?`
3. Write nothing until the user says yes.
4. Detect the environment.
5. Write the entry with the template below. Redact it (see "Redact before writing").
6. Add the entry to `INDEX.md`. Create `INDEX.md` with a `# Knowledge base` title if it does not exist.
7. Tell the user the path of the new file. Remind them to commit `.knowledge-base/` with their change.

## Detect the environment

```sh
uname -sm
grep -qi microsoft /proc/version 2>/dev/null && echo wsl
```

- `os`: `Darwin` is `macos`. `Linux` is `linux`, or `wsl` if the second command prints `wsl`. `MINGW*`, `MSYS*` or `CYGWIN*` is `windows`.
- `arch`: `arm64` and `aarch64` are `arm64`. `x86_64` and `amd64` are `x86_64`.

Set `scope: listed` only when there is evidence that the problem depends on the OS or architecture. Otherwise use `scope: all`.

## Redact before writing

Entries are committed to the repository. Before writing, replace:

- Tokens, passwords, API keys and connection strings with placeholders such as `<API_TOKEN>` or `<DATABASE_URL>`.
- Internal hostnames, IP addresses and customer names with `<DB_HOST>`, `<INTERNAL_IP>`, `<CUSTOMER>`.
- Email addresses with `<EMAIL>`.
- Absolute home paths with `~/`.

Keep the rest of the error text literal, because the lookup depends on it.

## Entry template

```markdown
---
title: <one line describing the problem>
category: <category>
symptoms: <what the developer sees, in one line>
error_signature: "<the most distinctive literal fragment of the error>"
environments:
  - os: <macos | linux | wsl | windows>
    arch: <arm64 | x86_64>
scope: <all | listed>
tags: [<tag>, <tag>]
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

## Symptom

<The command that was run and the relevant part of the output, redacted.>

## Cause

<Why it happens, in plain words.>

## Solution

<The exact steps or commands that fixed it.>

## Verify

<How to check that it is fixed.>
```
