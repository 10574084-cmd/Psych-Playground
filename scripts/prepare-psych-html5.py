#!/usr/bin/env python3
"""Apply minimal, repeatable browser-target patches to Psych Engine 0.7.3."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
project = root / "Project.xml"
main = root / "source" / "Main.hx"
paths = root / "source" / "backend" / "Paths.hx"

xml = project.read_text(encoding="utf-8")
old = '<define name="DISCORD_ALLOWED" />'
new = '<define name="DISCORD_ALLOWED" if="desktop" />'
if old in xml:
    xml = xml.replace(old, new, 1)
elif new not in xml:
    raise SystemExit("Could not locate the Discord define in Project.xml")
project.write_text(xml, encoding="utf-8")

source = main.read_text(encoding="utf-8")
old_state = "initialState: TitleState, // initial game state"
new_state = "initialState: #if html5 states.FreeplayState #else TitleState #end, // initial game state"
if old_state in source:
    source = source.replace(old_state, new_state, 1)
elif new_state not in source:
    raise SystemExit("Could not locate the initialState declaration in source/Main.hx")
main.write_text(source, encoding="utf-8")

# Paths.loadAnimateAtlas accepts asset paths. The HTML5 target has no sys.io.File.
path_source = paths.read_text(encoding="utf-8")
for variable in ("spriteJson", "animationJson"):
    old_line = f"{variable} = File.getContent({variable});"
    new_block = (
        "#if sys\n"
        f"\t\t\t{variable} = File.getContent({variable});\n"
        "#else\n"
        f"\t\t\t{variable} = OpenFlAssets.getText({variable});\n"
        "#end"
    )
    if old_line in path_source:
        path_source = path_source.replace(old_line, new_block, 1)
    elif new_block not in path_source:
        raise SystemExit(f"Could not locate {old_line} in Paths.hx")
paths.write_text(path_source, encoding="utf-8")


# Avoid the browser DOM's js.html.Option shadowing Psych's options.Option.
imports = root / "source" / "import.hx"
import_source = imports.read_text(encoding="utf-8")
if "import options.Option;" not in import_source:
    import_source = import_source.replace("#if !macro\n", "#if !macro\nimport options.Option;\n", 1)
imports.write_text(import_source, encoding="utf-8")

# File-system editor discovery is not available to a browser build.
editor = root / "source" / "states" / "editors" / "CharacterEditorState.hx"
editor_source = editor.read_text(encoding="utf-8")
old_editor = (
    "\t\tfor (folder in foldersToCheck)\n"
    "\t\t\tfor (file in FileSystem.readDirectory(folder))"
)
new_editor = (
    "#if sys\n"
    "\t\tfor (folder in foldersToCheck)\n"
    "\t\t\tfor (file in FileSystem.readDirectory(folder))"
)
if old_editor in editor_source:
    editor_source = editor_source.replace(old_editor, new_editor, 1)
    marker = "\n\t\t}\n"
    start = editor_source.index(new_editor)
    close = editor_source.find(marker, start)
    if close < 0:
        raise SystemExit("Could not close CharacterEditorState file-system guard")
    editor_source = editor_source[:close] + "\n\t\t#end" + editor_source[close:]
elif new_editor not in editor_source:
    raise SystemExit("Could not locate CharacterEditorState directory scan")
editor.write_text(editor_source, encoding="utf-8")

# CoolUtil.openFolder cannot open local folders from a browser.
cool = root / "source" / "backend" / "CoolUtil.hx"
cool_source = cool.read_text(encoding="utf-8")
cool_source = cool_source.replace(
    'FlxG.error("Platform is not supported for CoolUtil.openFolder");',
    'trace("Platform is not supported for CoolUtil.openFolder in a browser.");',
    1
)
cool.write_text(cool_source, encoding="utf-8")

# flxanimate's development branch still has desktop-only File.getContent calls
# in loadAtlasEx. Use the OpenFL asset system on browser targets.
lib_root = Path.home() / "haxelib" / "flxanimate"
candidates = list(lib_root.rglob("FlxAnimate.hx"))
if not candidates:
    raise SystemExit(f"Could not find flxanimate source under {lib_root}")
for flx_file in candidates:
    fa = flx_file.read_text(encoding="utf-8")
    replacements = {
        "if(trimmed == '.json') myJson = sys.io.File.getContent(myJson); //is a path": (
            "if(trimmed == '.json') {\n"
            "\t\t\t#if sys\n"
            "\t\t\tmyJson = sys.io.File.getContent(myJson);\n"
            "\t\t\t#else\n"
            "\t\t\tmyJson = openfl.Assets.getText(myJson);\n"
            "\t\t\t#end\n"
            "\t\t\t}"
        ),
        "myData = sys.io.File.getContent(pathOrStr);": (
            "#if sys\n"
            "\t\t\tmyData = sys.io.File.getContent(pathOrStr);\n"
            "\t\t\t#else\n"
            "\t\t\tmyData = openfl.Assets.getText(pathOrStr);\n"
            "\t\t\t#end"
        ),
    }
    for old_text, new_text in replacements.items():
        if old_text in fa:
            fa = fa.replace(old_text, new_text)
        elif new_text not in fa:
            raise SystemExit(f"Could not find flxanimate HTML5 file access in {flx_file}")
    flx_file.write_text(fa, encoding="utf-8")


renderer_file = lib_root / "git" / "flxanimate" / "display" / "FlxAnimateFilterRenderer.hx"
if not renderer_file.exists():
    matches = list(lib_root.rglob("FlxAnimateFilterRenderer.hx"))
    if not matches:
        raise SystemExit("Could not find flxanimate filter renderer")
    renderer_file = matches[0]
renderer_source = renderer_file.read_text(encoding="utf-8")

# The renderer uses private OpenFL Canvas internals and an OpenGL context.
# For HTML5, gracefully skip those optional filter/blend passes.
if "renderer = new OpenGLRenderer(FlxG.game.stage.context3D);" in renderer_source:
    renderer_source = renderer_source.replace(
        "renderer = new OpenGLRenderer(FlxG.game.stage.context3D);",
        "#if !(js && html5)\n\t\trenderer = new OpenGLRenderer(FlxG.game.stage.context3D);\n\t\t#end",
        1
    )
for method, fallback in (
    ("applyFilter", "return bmp;"),
    ("applyBlend", "return bitmap;"),
    ("graphicstoBitmapData", "return gfx.__bitmap;"),
):
    pattern = re.compile(r"(\tpublic function " + method + r"\([^\n]*\)\s*\{)(.*?)(\n\t\})", re.S)
    match = pattern.search(renderer_source)
    if not match:
        raise SystemExit(f"Could not locate flxanimate {method} method")
    if "#if (js && html5)" not in match.group(2):
        replacement = (
            match.group(1) + "\n"
            + "\t\t#if (js && html5)\n"
            + "\t\t" + fallback + "\n"
            + "\t\t#else"
            + match.group(2)
            + "\n\t\t#end"
            + match.group(3)
        )
        renderer_source = renderer_source[:match.start()] + replacement + renderer_source[match.end():]
renderer_file.write_text(renderer_source, encoding="utf-8")

print("Psych Engine 0.7.3 prepared for HTML5: native Freeplay startup, browser-safe imports and file reads, with desktop-only integrations disabled.")
