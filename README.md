# itcrowd Claude Code marketplace

Claude Code plugins built by itcrowd for itcrowd developers. You enable them per client project, and every developer who opens that project in Claude Code gets them.

> Work in progress. The marketplace has one category with one plugin today.

## How it is organized

Plugins are grouped in **categories**. Each plugin is small and does one job, and a project enables plugins one by one. To use a whole category, enable every plugin of its table in [Plugins](#plugins).

## Plugins

### Project knowledge

Helps developers understand a project and keep what the team learns about it.

| Plugin | What it does |
|---|---|
| [`kb-central`](plugins/project-knowledge/kb-central) | Connects the project to the team's central knowledge base, a private repository with a wiki per project. Claude reads the wiki when an error appears, and sends the problems the team solves as GitHub issues after you confirm them. Needs `KB_CENTRAL_REPO` in the project settings and `gh` logged in on every machine. |

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

Create or edit `.claude/settings.json` in the root of the project repository and commit it:

```json
{
  "extraKnownMarketplaces": {
    "itcrowd": {
      "source": { "source": "github", "repo": "itcrowdarg/skills" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "kb-central@itcrowd": true
  },
  "env": {
    "KB_CENTRAL_REPO": "itcrowdarg/kb"
  }
}
```

- `extraKnownMarketplaces` tells Claude Code where the `itcrowd` marketplace lives.
- `autoUpdate: true` keeps the plugins up to date on every developer's machine. See [Updates](#updates).
- `enabledPlugins` lists the plugins the project uses, as `<plugin>@itcrowd`.
- `env` holds the settings some plugins need. Each plugin's README lists them: `kb-central` needs `KB_CENTRAL_REPO`, and the project must be listed in the central repository. See [its README](plugins/project-knowledge/kb-central).

### Choose categories and plugins

Pick plugins from the tables in [Plugins](#plugins). To take a whole category, list all its plugins. To leave one out, don't list it.

Example with planned categories and plugins that don't exist yet. The project takes all of a `dev-workflow` category with two plugins, nothing from `design`, and `kb-central` from `project-knowledge`:

```json
"enabledPlugins": {
  "commit-messages@itcrowd": true,
  "code-review@itcrowd": true,
  "kb-central@itcrowd": true
}
```

There is no single entry that enables a whole category. A plugin can declare other plugins as dependencies, but enabling it from a project's settings doesn't install them, so every developer would have to install them by hand.

### From the command line

The same setup with the CLI, from the root of the project:

```sh
claude plugin marketplace add itcrowdarg/skills --scope project
claude plugin install kb-central@itcrowd --scope project
```

The commands don't set `autoUpdate` or `env`. Add `"autoUpdate": true` to the `itcrowd` entry of `.claude/settings.json`, and the `env` values the plugins need, by hand.

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
    "kb-central@itcrowd": false
  }
}
```

## Updates

With `"autoUpdate": true` in the project settings:

1. After your first message in a session, Claude Code waits a random delay of up to ten minutes, then pulls the `itcrowd` marketplace and updates its plugins on disk.
2. When a plugin changed, you see `Plugin updated: <name> · Run /reload-plugins to apply`.
3. Run `/reload-plugins` to use the new version now. Otherwise it loads the next time you start Claude Code.

Without `autoUpdate`, update by hand:

```sh
claude plugin marketplace update itcrowd
```

Each developer can also turn auto-update on or off in `/plugin` > **Marketplaces** > `itcrowd`. The value in the project settings wins over that toggle.

Auto-update doesn't run when `DISABLE_AUTOUPDATER=1`, `DISABLE_UPDATES=1` or `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` is set, unless `FORCE_AUTOUPDATE_PLUGINS=1` is set too.

## Troubleshooting

| Problem | Fix |
|---|---|
| The plugins don't show up and there is no error | You haven't trusted the folder. Claude Code ignores the project's marketplace without a message until you do. Start `claude` in the project root and accept the trust dialog. |
| The marketplace fails to clone and you have no GitHub SSH key | Claude Code tries SSH first for GitHub. Set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` to clone over HTTPS. |
| A plugin change from this repository doesn't reach you | Check that `autoUpdate` is `true` in the project settings, or run `claude plugin marketplace update itcrowd`. Then run `/reload-plugins`. |
| `claude -p` or CI doesn't load the plugins | The folder must be trusted first, in an interactive session. Set `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1` to wait for the plugins before the first query. |

## Official documentation

- [Plugins overview](https://code.claude.com/docs/en/plugins/overview)
- [Install and manage plugins](https://code.claude.com/docs/en/plugins/install)
- [Require plugins per repository](https://code.claude.com/docs/en/plugins/org)
- [Workspace trust](https://code.claude.com/docs/en/permissions)
- [Plugin CLI commands](https://code.claude.com/docs/en/plugins/cli-reference)
- [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference)
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference)
- [How plugins load and auto-update](https://code.claude.com/docs/en/plugins/loading)
- [Skills](https://code.claude.com/docs/en/skills)
- [Hooks](https://code.claude.com/docs/en/hooks)

## Contributing

Read [CLAUDE.md](CLAUDE.md) before you add or change a plugin.

## License

[MIT](LICENSE)
