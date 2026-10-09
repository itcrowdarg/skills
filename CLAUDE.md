# itcrowd Claude Code marketplace

This repository is a Claude Code plugin marketplace named `itcrowd`. Client projects declare it in their `.claude/settings.json`, and their developers get the plugins when they trust the project folder.

## Layout

```
.
├── .claude-plugin/marketplace.json   # marketplace catalog: one entry per plugin
├── plugins/<category>/<plugin>/
│   ├── .claude-plugin/plugin.json    # plugin manifest
│   ├── skills/<skill>/SKILL.md
│   ├── hooks/hooks.json              # optional
│   └── README.md                     # optional, what the plugin does and how to use it
├── README.md                         # for users: install and use
└── LICENSE                           # MIT
```

## Rules

- Commit messages follow Conventional Commits: `type(scope): message`. The scope is the plugin name, or `marketplace` for repository-wide changes.
- Every plugin lives in `plugins/<category>/<plugin>/` and its marketplace entry uses a relative `source` (`./plugins/<category>/<plugin>`). Plugins with a relative source load from the marketplace clone without `claude plugin install`. A plugin in an external repository would force every developer to install it by hand.
- Prefer several small plugins over one large plugin. A plugin is enabled as a whole, hooks included, so each project enables only the plugins it needs.
- Categories group plugins in the folder tree, in the `category` field of each marketplace entry, and in the sections of `README.md`. Category names are kebab-case: `project-knowledge`, `discovery`, `dev-workflow`, `quality`, `delivery`, `client-communication`, `design`.
- Categories are only for organization. There are no category or bundle plugins: a plugin enabled from a project's `.claude/settings.json` doesn't install its `dependencies`, so each developer would have to install them by hand. Projects list every plugin they want in `enabledPlugins`.
- Hooks run on macOS, Linux and WSL. Write them as a small POSIX `sh` launcher that finds Python 3 (`python3`, then `python`) and runs a Python script that uses only the standard library. If Python is missing, the hook exits 0 and prints a `systemMessage` that explains what to install. A hook must never break the session. Don't depend on `jq`.
- Skills tell Claude to ask before writing files in the client repository.

## Change a plugin

1. Make the change.
2. Bump `version` in the plugin's `.claude-plugin/plugin.json`. Claude Code pins a plugin to its `version`, so without a bump the change doesn't reach users.
3. Run `claude plugin validate .` from the repository root. It must pass with no errors.
4. Update the plugin's row in `README.md` if its purpose changed.

## Add a plugin

1. Create `plugins/<category>/<plugin>/.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, `license` and `repository`.
2. Add an entry to `.claude-plugin/marketplace.json` with `name`, `source`, `category` and `description`.
3. Add a row to the category's table in `README.md` and add the plugin id to its category in "How it is organized". A new category also gets its own section and its own row.
4. Run `claude plugin validate .`.

## Documentation links

`README.md` links to the official Claude Code documentation at `https://code.claude.com/docs/en/`. Before you change anything that describes Claude Code behavior (installation, trust, settings keys, CLI commands):

1. Check that every link still answers.
2. Read the linked page as raw Markdown by appending `.md` to the URL (for example `https://code.claude.com/docs/en/plugins/org.md`). Don't rely on a summary of the page.
3. If the page changed, update the link or the text so that `README.md` matches the official behavior.
