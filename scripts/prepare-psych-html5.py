#!/usr/bin/env python3
"""Apply minimal, repeatable changes needed for the Psych Engine 0.7.3 web target."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
project = root / "Project.xml"
main = root / "source" / "Main.hx"

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

print("Psych Engine 0.7.3 prepared: browser starts in native Freeplay; Discord RPC remains desktop-only.")
