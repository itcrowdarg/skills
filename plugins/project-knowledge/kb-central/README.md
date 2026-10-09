# kb-central

Connects a project to the team's central knowledge base: a private GitHub repository that holds a wiki for every project. Developers send what they learn as GitHub issues, and Claude reads the wiki when an error appears or a question comes up.

The plugin never writes to the central repository other than by creating issues. A scheduled routine in that repository validates the issues and turns them into wiki pages through a pull request that a person reviews.

## What it adds

| Piece | What it does |
|---|---|
| `kb-search` skill | When an error appears or you ask how something works, Claude looks for the answer in the project's wiki and cites the page. |
| `kb-submit` skill | After a problem is solved, or when you ask, Claude drafts an issue, redacts secrets and personal data, shows it to you and creates it only after you say yes. |
| `SessionStart` hook | Loads `projects/<name>/index.md` from the central repository into the session, so Claude knows which pages exist. |

`<name>` is the name of the project's repository in lowercase, taken from `git remote get-url origin`.

## Requirements

- [GitHub CLI](https://cli.github.com/) (`gh`), logged in with `gh auth login` to an account with read access to the central repository.
- Python 3, standard library only.
- The project is a git repository with a GitHub remote named `origin`.

## Set it up in a project

Enable the plugin and name the central repository in the project's `.claude/settings.json`:

```json
{
  "env": {
    "KB_CENTRAL_REPO": "itcrowdarg/kb"
  },
  "enabledPlugins": {
    "kb-central@itcrowd": true
  }
}
```

`env` values from the project settings apply after you trust the folder. Without `KB_CENTRAL_REPO`, the hook shows a one-line message and the skills explain how to set it.

## When something fails

The hook never stops the session. If `gh` is missing, GitHub doesn't answer within 5 seconds, or you have no access, the session starts with a one-line message. When GitHub can't be reached, the hook uses the last copy of the index it downloaded, kept in the plugin's data directory.

If `gh` can't create the issue, `kb-submit` prints the title and the body and gives you the link to open the issue by hand.

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
