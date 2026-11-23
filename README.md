# FNF Playground Psych

FNF Playground Psych uses the **real Psych Engine 0.7.3 Haxe source**, compiled to HTML5 by GitHub Actions and hosted on GitHub Pages.

## Current web integration
- The landing menu contains **Play**, **Options**, and **Mods**.
- **Play** opens the compiled Psych Engine runtime. The HaxeFlixel/OpenFL game starts in Psych Engine's Freeplay state.
- The normal Psych Engine game logic, song loading, charts, character animations, notes, health, and audio are provided by the compiled engine rather than a JavaScript imitation.
- Boyfriend is provided by Psych Engine's bundled base-game assets when no custom mod is active.
- Options and the ZIP character library remain in the Playground shell.

## Build pipeline
The workflow checks out the exact Psych Engine 0.7.3 source commit `2dfa27773a3668e0c1b043a3fb4348942c8a6fb3`, installs the Haxe 4.3.2 / HaxeFlixel 5.5 dependency set recorded for the Psych 0.7.x generation, patches only the HTML5 entry point and desktop-only Discord integration, compiles with Lime for the `html5` target, then deploys the generated engine files with GitHub Pages.

The engine source ZIP supplied for this project corresponds to the official `0.7.3` tag and the same commit.

## Known web limitations
- Psych Engine 0.7.3 enables its native folder-based mod loader and Lua/HScript scripting only for desktop builds. The Playground's ZIP library can currently inspect character JSON/XML/PNG files, but it does **not yet inject those mods into the compiled Haxe runtime**.
- The original 0.7.3 PlayState is single-player. The two-player button is shown as planned but is not yet wired into Psych Engine's gameplay code.
- The browser build starts directly in Freeplay so the Playground landing menu stays limited to Play, Options, and Mods.
- Video cutscenes and desktop-only integrations are not included in the HTML5 build.

## GitHub Pages
The workflow at `.github/workflows/pages.yml` builds the engine and deploys the `playground/site` folder on pushes to `main` and manual runs. In **Settings → Pages → Build and deployment**, choose **GitHub Actions** as the source.

FNF Playground Psych is an unofficial fan project and is not affiliated with the Funkin' Crew. Psych Engine is authored by Shadow Mario and contributors. Respect the Psych Engine license and the rights and terms attached to every mod you import.
