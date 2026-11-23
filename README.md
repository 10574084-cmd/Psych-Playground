# FNF Playground Psych

Web adaptation inspired by Psych Engine 0.7.3 character data, deployed as a static site on GitHub Pages.

## Features in this first web build
- Main menu with only **Play**, **Options** and **Mods**.
- Boyfriend is the default character, even when no mods are imported.
- Client-side ZIP import for Psych-style character JSON + Sparrow XML atlas + PNG sprite sheets.
- Character selection for each player.
- Solo mode and local 2-player mode (P1: WASD, P2: arrow keys).
- Optional touch controls and saved local settings.

## GitHub Pages
The workflow at \`.github/workflows/pages.yml\` deploys the \`site/\` folder on pushes to \`main\` and manual runs. In **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source. The first deployment may require enabling Pages for this repository.

## Compatibility
This is a JavaScript browser adaptation, not the original Haxe executable. It reads basic Psych character JSON, XML atlas and PNG sprites. It does not run Psych Lua scripts or load full songs/stages yet. The default Boyfriend data and sprites are loaded from the public Psych Engine 0.7.3 source tree. Imported ZIP files are processed locally in browser memory; they are not uploaded to GitHub and must be re-imported after refreshing.

FNF Playground Psych is an unofficial fan experiment and is not affiliated with the Funkin' Crew. Psych Engine credits include Shadow Mario (programmer), Riveren (artist), and its contributors. Respect the original engine license and the rights/terms attached to every mod you import.
