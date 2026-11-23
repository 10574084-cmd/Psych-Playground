# FNF Playground Psych

FNF Playground Psych boots directly into a **native Haxe menu inside Psych Engine 0.7.3**. The web page is the compiled Psych Engine HTML5 build itself; there is no external JavaScript menu, iframe shell, AI engine, or canvas-based gameplay replacement.

## Native in-engine menu
- **Play** opens Psych Engine's native Freeplay state.
- **Options** opens Psych Engine's native options state.
- **Mods** opens the original Psych mod manager on desktop builds. On HTML5, it opens a native in-engine notice explaining that Psych 0.7.3's folder-based mod loader is disabled for browser targets.
- Boyfriend is rendered by Psych Engine as the menu character.
- Returning from Freeplay, Options, or the desktop Mod Manager returns to the Playground menu.

The browser menu supports keyboard arrows + Enter and mouse selection. No AI services or AI model are used.

## Build pipeline
The workflow checks out the exact Psych Engine 0.7.3 source commit `2dfa27773a3668e0c1b043a3fb4348942c8a6fb3`, installs Haxe 4.3.2 and the HaxeFlixel 5.5 dependency set, applies browser-compatibility patches and adds the native Playground Haxe states, compiles with Lime for the `html5` target, then publishes the generated engine files directly at the GitHub Pages root.

The engine source ZIP supplied for this project corresponds to the official `0.7.3` tag and the same commit.

## Current browser limitations
- Psych Engine 0.7.3's native folder-based mod loader and Lua/HScript mod support are desktop-only. The HTML5 Mods screen is native, but ZIP importing and injection into the runtime are not connected yet.
- The original 0.7.3 PlayState is single-player. Two-player gameplay still needs a native PlayState adaptation.
- Video cutscenes and desktop-only integrations are not included in the HTML5 build.

## GitHub Pages
The workflow at `.github/workflows/pages.yml` compiles the engine and deploys the generated `playground/site` output on pushes to `main` and manual runs. In **Settings → Pages → Build and deployment**, choose **GitHub Actions** as the source.

FNF Playground Psych is an unofficial fan project and is not affiliated with the Funkin' Crew. Psych Engine is authored by Shadow Mario and contributors. Respect the Psych Engine license and the rights and terms attached to every mod you import.
