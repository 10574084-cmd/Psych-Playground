#!/usr/bin/env python3
"""Apply minimal, repeatable browser-target patches to Psych Engine 0.7.3."""
from pathlib import Path
import re
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

# Native Playground menu: this replaces the external HTML shell and the default title/menu states.
main_source = main.read_text(encoding="utf-8")
if "import states.PlaygroundMenuState;" not in main_source:
    main_source = main_source.replace("import states.TitleState;", "import states.TitleState;\nimport states.PlaygroundMenuState;", 1)
main.write_text(main_source, encoding="utf-8")

old_states = (
    "initialState: TitleState, // initial game state",
    "initialState: #if html5 states.FreeplayState #else TitleState #end, // initial game state",
)
new_initial = "initialState: PlaygroundMenuState, // initial game state"
if new_initial not in main_source:
    for old_state in old_states:
        if old_state in main_source:
            main_source = main_source.replace(old_state, new_initial, 1)
            break
    else:
        raise SystemExit("Could not locate Main.hx initialState for the native Playground menu")
main.write_text(main_source, encoding="utf-8")

# Keep navigation inside the Playground Haxe states after Play, Options, and desktop Mods.
for relative in (
    "source/states/FreeplayState.hx",
    "source/states/ModsMenuState.hx",
    "source/options/OptionsState.hx",
):
    route_file = root / relative
    route_source = route_file.read_text(encoding="utf-8")
    if relative == "source/options/OptionsState.hx" and "import states.PlaygroundMenuState;" not in route_source:
        route_source = route_source.replace(
            "import states.MainMenuState;",
            "import states.MainMenuState;\\nimport states.PlaygroundMenuState;",
            1
        )
    route_source = route_source.replace(
        "MusicBeatState.switchState(new MainMenuState());",
        "MusicBeatState.switchState(new PlaygroundMenuState());"
    )
    route_file.write_text(route_source, encoding="utf-8")

menu_file = root / "source" / "states" / "PlaygroundMenuState.hx"
menu_source = r'''package states;

import objects.Character;
import options.OptionsState;

class PlaygroundMenuState extends MusicBeatState
{
    private var menuItems:Array<FlxText> = [];
    private var labels:Array<String> = ["PLAY", "OPTIONS", "MODS"];
    private var curSelected:Int = 0;
    private var selectedSomething:Bool = false;
    private var boyfriend:Character;

    override function create():Void
    {
        Paths.clearStoredMemory();
        Mods.loadTopMod();
        FlxG.mouse.visible = true;

        if (FlxG.sound.music == null)
            FlxG.sound.playMusic(Paths.music("freakyMenu"), 0.7, true);

        var bg:FlxSprite = new FlxSprite().loadGraphic(Paths.image("menuBG"));
        bg.antialiasing = ClientPrefs.data.antialiasing;
        bg.setGraphicSize(Std.int(bg.width * 1.175));
        bg.updateHitbox();
        bg.screenCenter();
        add(bg);

        var shade:FlxSprite = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
        shade.alpha = 0.32;
        add(shade);

        var panel:FlxSprite = new FlxSprite(74, 145).makeGraphic(520, 430, FlxColor.BLACK);
        panel.alpha = 0.48;
        add(panel);

        var title:FlxText = new FlxText(105, 62, 650, "FNF PLAYGROUND", 56);
        title.setFormat(Paths.font("vcr.ttf"), 56, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
        title.borderSize = 3;
        add(title);

        var subtitle:FlxText = new FlxText(110, 124, 600, "PSYCH ENGINE 0.7.3", 18);
        subtitle.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.CYAN, LEFT);
        add(subtitle);

        boyfriend = new Character(785, 235, "bf", true);
        boyfriend.setGraphicSize(Std.int(boyfriend.width * 0.88));
        boyfriend.updateHitbox();
        boyfriend.dance();
        add(boyfriend);

        for (i in 0...labels.length)
        {
            var item:FlxText = new FlxText(132, 225 + i * 104, 420, "", 42);
            item.setFormat(Paths.font("vcr.ttf"), 42, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
            item.borderSize = 2;
            item.scrollFactor.set();
            menuItems.push(item);
            add(item);
        }

        var hint:FlxText = new FlxText(94, FlxG.height - 54, FlxG.width - 188,
            "UP / DOWN  SELECT          ENTER  CONFIRM          ESC  BACK", 16);
        hint.setFormat(Paths.font("vcr.ttf"), 16, FlxColor.WHITE, CENTER);
        hint.alpha = 0.9;
        add(hint);

        changeSelection(0);
        super.create();
    }

    override function update(elapsed:Float):Void
    {
        if (!selectedSomething)
        {
            if (controls.UI_UP_P) changeSelection(-1);
            if (controls.UI_DOWN_P) changeSelection(1);

            for (i in 0...menuItems.length)
            {
                if (FlxG.mouse.overlaps(menuItems[i]))
                {
                    if (curSelected != i) changeSelection(i - curSelected);
                    if (FlxG.mouse.justPressed) acceptSelection();
                }
            }

            if (controls.ACCEPT) acceptSelection();
        }

        super.update(elapsed);
    }

    private function changeSelection(change:Int):Void
    {
        curSelected = (curSelected + change + labels.length) % labels.length;
        FlxG.sound.play(Paths.sound("scrollMenu"), 0.55);

        for (i in 0...menuItems.length)
        {
            var selected:Bool = i == curSelected;
            menuItems[i].text = (selected ? ">  " : "   ") + labels[i];
            menuItems[i].color = selected ? FlxColor.CYAN : FlxColor.WHITE;
            menuItems[i].alpha = selected ? 1 : 0.68;
        }
    }

    private function acceptSelection():Void
    {
        if (selectedSomething) return;
        selectedSomething = true;
        FlxG.sound.play(Paths.sound("confirmMenu"));

        switch (curSelected)
        {
            case 0:
                PlayState.isStoryMode = false;
                MusicBeatState.switchState(new FreeplayState());

            case 1:
                OptionsState.onPlayState = false;
                MusicBeatState.switchState(new OptionsState());

            case 2:
                #if MODS_ALLOWED
                MusicBeatState.switchState(new ModsMenuState());
                #else
                MusicBeatState.switchState(new PlaygroundModsState());
                #end
        }
    }
}
'''
menu_file.write_text(menu_source, encoding="utf-8")

mods_file = root / "source" / "states" / "PlaygroundModsState.hx"
mods_source = r'''package states;

class PlaygroundModsState extends MusicBeatState
{
    override function create():Void
    {
        var bg:FlxSprite = new FlxSprite().loadGraphic(Paths.image("menuDesat"));
        bg.color = 0xFF665AFF;
        bg.antialiasing = ClientPrefs.data.antialiasing;
        bg.screenCenter();
        add(bg);

        var title:FlxText = new FlxText(80, 105, FlxG.width - 160, "MODS", 56);
        title.setFormat(Paths.font("vcr.ttf"), 56, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
        title.borderSize = 3;
        add(title);

        var message:FlxText = new FlxText(150, 265, FlxG.width - 300,
            "BROWSER BUILD\n\nPsych Engine 0.7.3 uses a desktop folder-based mod loader.\nThat loader is disabled in HTML5 builds.\n\nZIP character importing still needs a native browser asset bridge.", 25);
        message.setFormat(Paths.font("vcr.ttf"), 25, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
        message.borderSize = 2;
        add(message);

        var back:FlxText = new FlxText(0, FlxG.height - 85, FlxG.width, "ESC  /  BACK  —  MAIN MENU", 20);
        back.setFormat(Paths.font("vcr.ttf"), 20, FlxColor.CYAN, CENTER);
        add(back);

        super.create();
    }

    override function update(elapsed:Float):Void
    {
        super.update(elapsed);
        if (controls.BACK || controls.ACCEPT)
            MusicBeatState.switchState(new PlaygroundMenuState());
    }
}
'''
mods_file.write_text(mods_source, encoding="utf-8")

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
    "\t\t\tfor (file in FileSystem.readDirectory(folder))\n"
    "\t\t\t\tif(file.toLowerCase().endsWith('.json'))\n"
    "\t\t\t\t{\n"
    "\t\t\t\t\tvar charToCheck:String = file.substr(0, file.length - 5);\n"
    "\t\t\t\t\tif(!characterList.contains(charToCheck))\n"
    "\t\t\t\t\t\tcharacterList.push(charToCheck);\n"
    "\t\t\t\t}"
)
new_editor = "#if sys\n" + old_editor + "\n#end"
if old_editor in editor_source:
    editor_source = editor_source.replace(old_editor, new_editor, 1)
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
    pattern = re.compile(r"(?ms)^([ \t]*)public function " + method + r"\([^\n]*\)\s*\{(.*?)(^\1\})")
    match = pattern.search(renderer_source)
    if not match:
        raise SystemExit(f"Could not locate flxanimate {method} method")
    if not match.group(2).lstrip().startswith("#if (js && html5)"):
        whole = match.group(0)
        signature = whole[:whole.find("{") + 1]
        indent = match.group(1)
        replacement = (
            signature + "\n"
            + "\t\t#if (js && html5)\n"
            + "\t\t" + fallback + "\n"
            + "\t\t#else"
            + match.group(2)
            + "\n\t\t#end\n"
            + match.group(3)
        )
        renderer_source = renderer_source[:match.start()] + replacement + renderer_source[match.end():]
renderer_file.write_text(renderer_source, encoding="utf-8")

print("Psych Engine 0.7.3 prepared for HTML5: native Freeplay startup, browser-safe imports and file reads, with desktop-only integrations disabled.")
