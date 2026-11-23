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

print("Psych Engine 0.7.3 prepared for HTML5: native Freeplay startup, desktop-only Discord, and browser-safe asset text reads.")
