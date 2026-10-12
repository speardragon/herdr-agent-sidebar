# herdr Agent Sidebar

A compact Agent sidebar for [herdr](https://herdr.dev): per-agent logo icons, one project header per workspace group, and status marks (optionally animated).

[한국어](README.ko.md)

## Requirements

- herdr 0.8.0+
- `python3` (standard library only)
- macOS or Linux

## Install

1. Install the plugin. The build step copies the bundled icon fonts into your user font directory (`~/Library/Fonts` on macOS, `~/.local/share/fonts` on Linux).

   ```sh
   herdr plugin install speardragon/herdr-agent-sidebar
   ```

2. Paste [`layout.toml`](layout.toml) into `~/.config/herdr/config.toml`. Comment out any existing `[ui]` / `[ui.sidebar.*]` tables first — TOML rejects a table defined twice.

3. Make your terminal fall back to the icon fonts. WezTerm example:

   ```lua
   config.font = wezterm.font_with_fallback({
     'JetBrains Mono', -- your usual font
     'Herdr Agent Icons Bounce',
     'Herdr Agent Icons Max',
   })
   ```

4. Reload: `herdr server reload-config`, then restart the terminal so it picks up the new fonts.

## Why a plugin?

The layout uses custom metadata tokens (`$agents_group`, `$agents_logo`, `$agents_mark`, `$agents_group_end`, `$agents_tab_*`). They are not herdr built-ins, so they are not in the herdr docs. This plugin computes them from `herdr agent list` / `workspace list` / `tab list` and reports them with `herdr pane report-metadata` on every relevant event. Without the plugin those tokens stay empty and herdr hides the rows.

## Actions

| Action | What it does |
|---|---|
| `sync` | Recompute every token now |
| `animations-on` / `animations-off` / `animations-toggle` | Spinner for `working`, bouncing `?` for `blocked` (off by default) |
| `animations-status` | Print whether the animation loop is enabled and running |

Runtime state (locks, animation flag, log) lives in `HERDR_PLUGIN_STATE_DIR`, not in the plugin checkout.

## Supported agent logos

claude, codex, opencode, pi, grok, agy. Other agents show `◇`. Add more by mapping agent ids to glyphs in the `logos` table in `sync.py`.

## Credits

Icon fonts come from [hhdebb/herdr-radar](https://github.com/hhdebb/herdr-radar) (MIT), a fork of [qintmb/herdr-icon-agent-ui](https://github.com/qintmb/herdr-icon-agent-ui). `Herdr Agent Icons Bounce` adds four `?` frames (U+E1D0–U+E1D3) to the Max font. See [`fonts/LICENSE`](fonts/LICENSE) and [`fonts/THIRD_PARTY_NOTICES.md`](fonts/THIRD_PARTY_NOTICES.md). Marks identify third-party products and do not imply affiliation or endorsement.
