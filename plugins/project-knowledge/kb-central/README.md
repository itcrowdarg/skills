# kb-central

Connects a project to the team's central knowledge base: a private GitHub repository that holds a wiki for every project. Developers send what they learn as GitHub issues, and Claude reads the wiki when an error appears or a question comes up.

The plugin never writes to the central repository other than by creating issues. A routine in that repository validates the issues and turns them into wiki pages through a pull request that a person reviews.

## What it adds

| Piece | What it does |
|---|---|
| `kb-search` skill | When an error appears or you ask how something works, Claude looks for the answer in the project's wiki and cites the page. |
| `kb-submit-troubleshooting` skill | After a problem is solved, or when you ask, Claude drafts an issue, redacts secrets and personal data, shows it to you and creates it only after you say yes. |
| `SessionStart` hook | Loads `projects/<org>/<repo>/index.md` from the central repository into the session, so Claude knows which pages exist. |

## Categories

The central repository keeps several kinds of knowledge, called categories. Each category has its own submit skill, named `kb-submit-<category>`, because each one is sent at a different moment and with a different text. Today there is one: `troubleshooting`, problems with their solution.

To add a category, add its definition and issue form to the central repository first, then a `kb-submit-<category>` skill here. Its `## Send` section must be the same as in the other submit skills: `tests/test_kb_central.py` checks it.

## Project id

Every project has an id, `<org>/<repo>` in lowercase. By default it comes from the path of `git remote get-url origin`, whatever the host, so SSH host aliases such as `git@github-work:org/repo.git` work.

Set `KB_CENTRAL_PROJECT` when the remote doesn't give the right id: a repository outside GitHub with subgroups, or several repositories (front end and back end) that share one wiki.

## Requirements

- [GitHub CLI](https://cli.github.com/) (`gh`), logged in with `gh auth login` to an account with read access to the central repository.
- Python 3, standard library only.
- The project is a git repository with a remote named `origin`, or sets `KB_CENTRAL_PROJECT`.

## Set it up in a project

Enable the plugin in the project's `.claude/settings.json`. Nothing else is needed: the central repository is `itcrowdarg/kb`, and it accepts entries from any project.

```json
{
  "enabledPlugins": {
    "kb-central@itcrowd": true
  }
}
```

Optional settings in `env`:

- `"KB_CENTRAL_PROJECT": "<org>/<repo>"`, if the project needs it (see [Project id](#project-id)).
- `"KB_CENTRAL_REPO": "<owner>/<name>"`, to use another central repository.

`env` values from the project settings apply after you trust the folder.

## Permissions

- In the default permission mode, Claude Code asks before it uses each skill for the first time (`Use skill "kb-central:kb-search"?`).
- The skills run `scripts/kb.py` without asking, during the turn in which they start. If you ask for changes to a draft, the next run asks once.
- `gh issue create` always asks: it is the second confirmation before anything leaves your machine.
- Each `gh api` call that reads a wiki page asks. To allow it for good, add a rule to `.claude/settings.local.json` in the project:

  ```json
  {
    "permissions": {
      "allow": ["Bash(gh api repos/itcrowdarg/kb/contents/*)"]
    }
  }
  ```

  The `*` also matches other options of `gh api`. With read access to the central repository, `gh api` can't change it anyway.

## When something fails

The hook never stops the session. If `gh` is missing or not logged in, GitHub doesn't answer within 5 seconds, or the project has no index yet, the session starts with a one-line message. The message appears when the session starts, not again after `/clear`, `/compact` or a resume. When GitHub can't be reached, the hook uses the last copy of the index it downloaded, kept in the plugin's data directory.

If `gh` can't create the issue, the submit skill gives you the file with the body and the link to open the issue by hand.

In auto mode, if your message contains a password or a token, the auto mode classifier can block the submit skill before it starts (`Denied by auto mode classifier · [Credential Leakage]`). Nothing is sent. Describe the problem again without the secret: the skill doesn't need it, and it would redact it anyway.

### Sandbox on macOS

`gh` fails TLS verification inside the Claude Code sandbox on macOS (`x509: OSStatus -26276`). If you use the sandbox, run `gh` outside it, as the [sandbox documentation](https://code.claude.com/docs/en/sandboxing#go-based-clis-fail-tls-verification-on-macos) recommends. Add this to `~/.claude/settings.json`:

```json
{
  "sandbox": {
    "excludedCommands": ["gh *"]
  }
}
```

The skills run `gh` as a single plain command so that this pattern matches it. The `SessionStart` hook doesn't run in the sandbox, so the index loads either way.
