# itcrowd Claude Code marketplace

Claude Code plugins built by itcrowd for itcrowd developers. You enable them per client project, and every developer who opens that project in Claude Code gets them.

> Work in progress. The marketplace has one plugin today.

## Plugins

Plugins are grouped by category. Each plugin is small and does one job, so a project enables only what it needs.

### Project knowledge

Helps developers understand a project and keep what the team learns about it.

| Plugin | What it does |
|---|---|
| [`knowledge-base`](plugins/project-knowledge/knowledge-base) | Keeps a knowledge base of recurring environment problems (build, Docker, deploy, dependencies, OS differences) in `.knowledge-base/` inside the project. Claude checks it when an error appears and offers to save new problems once they are solved. |
| [`kb-central`](plugins/project-knowledge/kb-central) | Connects the project to the team's central knowledge base, a private repository with a wiki per project. Claude reads the wiki when an error appears, and sends what the team learns as GitHub issues after you confirm them. |

### Planned categories

| Category | Scope |
|---|---|
| `discovery` | Turning an idea into a defined feature or project through a guided conversation |
| `dev-workflow` | Commits, pull requests, code review, branching |
| `quality` | Tests, QA, security review |
| `delivery` | Deploy, Docker, CI, infrastructure |
| `client-communication` | Progress reports, release notes, estimates |
| `design` | Figma to code, UI review |

## Add the plugins to a client project

Do this once per project. Usually the tech lead does it.

From the root of the project repository, run:

```sh
claude plugin marketplace add itcrowdarg/skills --scope project
claude plugin install knowledge-base@itcrowd --scope project
```

The two commands write this to `.claude/settings.json`. You can also write it by hand:

```json
{
  "extraKnownMarketplaces": {
    "itcrowd": {
      "source": { "source": "github", "repo": "itcrowdarg/skills" }
    }
  },
  "enabledPlugins": {
    "knowledge-base@itcrowd": true
  }
}
```

Commit `.claude/settings.json`.

## Use the plugins as a developer

1. Pull the project and run `claude` in its root.
2. Claude Code asks whether you trust the folder. Answer yes.
3. That's it. Claude Code registers the `itcrowd` marketplace and loads the plugins enabled in the project. You don't need to install anything.

To check it, run `/plugin` inside Claude Code. The `itcrowd` marketplace and its plugins are listed.

### Turn a plugin off on your machine only

Add this to `.claude/settings.local.json` in the project. Don't commit that file: it holds your personal settings, so add it to `.gitignore` if it isn't there yet.

```json
{
  "enabledPlugins": {
    "knowledge-base@itcrowd": false
  }
}
```

## Troubleshooting

| Problem | Fix |
|---|---|
| The plugins don't show up and there is no error | You haven't trusted the folder. Claude Code ignores the project's marketplace without a message until you do. Start `claude` in the project root and accept the trust dialog. |
| A plugin change from this repository doesn't reach you | Run `claude plugin marketplace update itcrowd` and restart Claude Code. |
| `claude -p` or CI doesn't load the plugins | The folder must be trusted first, in an interactive session. Set `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1` to wait for the plugins before the first query. |

## Official documentation

- [Plugins overview](https://code.claude.com/docs/en/plugins/overview)
- [Install and manage plugins](https://code.claude.com/docs/en/plugins/install)
- [Require plugins per repository](https://code.claude.com/docs/en/plugins/org)
- [Workspace trust](https://code.claude.com/docs/en/permissions)
- [Plugin CLI commands](https://code.claude.com/docs/en/plugins/cli-reference)
- [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference)
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference)
- [Skills](https://code.claude.com/docs/en/skills)
- [Hooks](https://code.claude.com/docs/en/hooks)

## Contributing

Read [CLAUDE.md](CLAUDE.md) before you add or change a plugin.

## License

[MIT](LICENSE)
