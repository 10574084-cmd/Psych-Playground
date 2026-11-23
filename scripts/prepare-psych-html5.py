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

# FreeplayState owns its normal week/song discovery. Do not synthesize WeekData here:
# an incomplete synthetic week can leave Freeplay with invalid selection state.

# Restore a valid starter week if HTML5 did not expose weekList/week JSON assets.
freeplay = root / "source" / "states" / "FreeplayState.hx"
freeplay_source = freeplay.read_text(encoding="utf-8")

# HTML5 fallback: avoid malformed external week JSON and boot with Psych's
# built-in starter week so Freeplay has valid song metadata.
reload_anchor = chr(9) * 2 + "WeekData.reloadWeekFiles(false);"
html5_week_bootstrap = (
    chr(9) * 2 + "#if html5" + chr(10)
    + chr(9) * 2 + 'var playgroundWeekName:String = "playgroundDefault";' + chr(10)
    + chr(9) * 2 + "var playgroundWeek:WeekData = new WeekData(WeekData.createWeekFile(), playgroundWeekName);" + chr(10)
    + chr(9) * 2 + "playgroundWeek.startUnlocked = true;" + chr(10)
    + chr(9) * 2 + 'playgroundWeek.weekBefore = "";' + chr(10)
    + chr(9) * 2 + "WeekData.weeksLoaded.set(playgroundWeekName, playgroundWeek);" + chr(10)
    + chr(9) * 2 + "WeekData.weeksList = [playgroundWeekName];" + chr(10)
    + chr(9) * 2 + "#end" + chr(10)
)
if reload_anchor not in freeplay_source:
    raise SystemExit("Could not locate WeekData.reloadWeekFiles in FreeplayState")
if html5_week_bootstrap not in freeplay_source:
    freeplay_source = freeplay_source.replace(reload_anchor, reload_anchor + chr(10) + html5_week_bootstrap, 1)

# In HTML5, bypass the external week list entirely. It can contain null metadata
# before Freeplay enumerates it; seed the normal Psych starter songs directly.
loop_start = chr(9) * 2 + 'for (i in 0...WeekData.weeksList.length) {'
loop_end = chr(9) * 2 + 'Mods.loadTopMod();'
start = freeplay_source.index(loop_start)
end = freeplay_source.index(loop_end, start)
original_week_loop = freeplay_source[start:end]
html5_loop = (
    chr(9) * 2 + '#if html5' + chr(10)
    + chr(9) * 2 + 'var pgWeekName:String = "playgroundDefault";' + chr(10)
    + chr(9) * 2 + 'var pgWeek:WeekData = new WeekData(WeekData.createWeekFile(), pgWeekName);' + chr(10)
    + chr(9) * 2 + 'pgWeek.startUnlocked = true;' + chr(10)
    + chr(9) * 2 + 'pgWeek.weekBefore = "";' + chr(10)
    + chr(9) * 2 + 'WeekData.weeksLoaded.set(pgWeekName, pgWeek);' + chr(10)
    + chr(9) * 2 + 'WeekData.weeksList = [pgWeekName];' + chr(10)
    + chr(9) * 2 + 'WeekData.setDirectoryFromWeek(pgWeek);' + chr(10)
    + chr(9) * 2 + 'addSong("Bopeebo", 0, "dad", FlxColor.fromRGB(146, 113, 253));' + chr(10)
    + chr(9) * 2 + 'addSong("Fresh", 0, "dad", FlxColor.fromRGB(146, 113, 253));' + chr(10)
    + chr(9) * 2 + 'addSong("Dad Battle", 0, "dad", FlxColor.fromRGB(146, 113, 253));' + chr(10)
    + chr(9) * 2 + '#else' + chr(10)
    + original_week_loop
    + chr(9) * 2 + '#end' + chr(10)
)
if '#if html5' + chr(10) not in original_week_loop:
    freeplay_source = freeplay_source[:start] + html5_loop + freeplay_source[end:]

# Browser builds may load partially populated week JSON. Guard fields that
# Psych's original FreeplayState assumes are always non-null.
week_entry = "var leWeek:WeekData = WeekData.weeksLoaded.get(WeekData.weeksList[i]);"
week_entry_guard = week_entry + """
			if (leWeek == null || leWeek.songs == null)
			{
				trace('[Playground] Skipping week with null metadata: ' + WeekData.weeksList[i]);
				continue;
			}"""
if week_entry not in freeplay_source:
    raise SystemExit("Could not locate Freeplay week metadata access")
if week_entry_guard not in freeplay_source:
    freeplay_source = freeplay_source.replace(week_entry, week_entry_guard, 1)
freeplay_source = freeplay_source.replace(
    "return (!leWeek.startUnlocked && leWeek.weekBefore.length > 0",
    "return (leWeek != null && !leWeek.startUnlocked && leWeek.weekBefore != null && leWeek.weekBefore.length > 0",
    1
)
freeplay_anchor = "\t\tMods.loadTopMod();"
freeplay_fallback = """\t\tif (songs.length == 0)
\t\t{
\t\t\tvar fallbackWeekName:String = "playgroundDefault";
\t\t\tvar fallbackWeek:WeekData = new WeekData(WeekData.createWeekFile(), fallbackWeekName);
\t\t\tfallbackWeek.weekBefore = "";
\t\t\tWeekData.weeksLoaded.set(fallbackWeekName, fallbackWeek);
\t\t\tWeekData.weeksList = [fallbackWeekName];
\t\t\tWeekData.setDirectoryFromWeek(fallbackWeek);
\t\t\tfor (song in fallbackWeek.songs)
\t\t\t{
\t\t\t\tvar colors:Array<Int> = cast song[2];
\t\t\t\tif (colors == null || colors.length < 3) colors = [146, 113, 253];
\t\t\t\taddSong(Std.string(song[0]), 0, Std.string(song[1]), FlxColor.fromRGB(colors[0], colors[1], colors[2]));
\t\t\t}
\t\t\ttrace("[Playground] Week metadata unavailable; loaded built-in starter songs.");
\t\t}
\n"""
if freeplay_fallback.strip() not in freeplay_source:
    if freeplay_anchor not in freeplay_source:
        raise SystemExit("Could not locate FreeplayState Mods.loadTopMod() anchor")
    freeplay_source = freeplay_source.replace(freeplay_anchor, freeplay_fallback + freeplay_anchor, 1)
    freeplay.write_text(freeplay_source, encoding="utf-8")

# Record the exact phase of Freeplay.create so a browser exception identifies
# the failing operation instead of only reporting the outer state constructor.
freeplay_source = freeplay.read_text(encoding="utf-8")
TAB = chr(9)
NL = chr(10)
stage_decl = TAB + "public static var playgroundDebugStage:String = 'Freeplay not started';" + NL
if "playgroundDebugStage" not in freeplay_source:
    class_anchor = "class FreeplayState extends MusicBeatState" + NL + "{"
    if class_anchor not in freeplay_source:
        raise SystemExit("Could not locate FreeplayState class declaration for diagnostics")
    freeplay_source = freeplay_source.replace(class_anchor, class_anchor + NL + stage_decl.rstrip(NL), 1)

stage_markers = [
    (TAB * 2 + "WeekData.reloadWeekFiles(false);", "reloadWeekFiles"),
    (TAB * 2 + "for (i in 0...WeekData.weeksList.length) {", "iterate weeksList"),
    (TAB * 3 + "if(weekIsLocked(WeekData.weeksList[i])) continue;", "check week lock"),
    (TAB * 3 + "var leWeek:WeekData = WeekData.weeksLoaded.get(WeekData.weeksList[i]);", "read week metadata"),
    (TAB * 3 + "for (j in 0...leWeek.songs.length)", "iterate week songs"),
    (TAB * 3 + "WeekData.setDirectoryFromWeek(leWeek);", "set week asset directory"),
    (TAB * 2 + "Mods.loadTopMod();", "load top mod"),
    (TAB * 2 + "bg = new FlxSprite().loadGraphic(Paths.image('menuDesat'));", "load Freeplay background"),
    (TAB * 2 + "for (i in 0...songs.length)", "build Freeplay song list"),
    (TAB * 2 + "bg.color = songs[curSelected].color;", "select initial song"),
    (TAB * 2 + "curDifficulty = Math.round(Math.max(0, Difficulty.defaultList.indexOf(lastDifficultyName)));", "set initial difficulty"),
    (TAB * 2 + "player = new MusicPlayer(this);", "create MusicPlayer"),
    (TAB * 2 + "changeSelection();", "initialize song selection"),
    (TAB * 2 + "updateTexts();", "initialize song text positions"),
]
for marker, stage in stage_markers:
    if marker not in freeplay_source:
        raise SystemExit("Could not locate Freeplay diagnostic marker: " + stage)
    tagged = TAB * 2 + "playgroundDebugStage = '" + stage + "';" + NL + marker
    if tagged not in freeplay_source:
        freeplay_source = freeplay_source.replace(marker, tagged, 1)
freeplay.write_text(freeplay_source, encoding="utf-8")

# Add mouse/touch-friendly song launching to browser Freeplay.
TAB = chr(9)
NL = chr(10)
player_field = TAB + "var player:MusicPlayer;"
mouse_field = player_field + NL + TAB + "var playgroundMouseAccept:Bool = false;"
if player_field not in freeplay_source:
    raise SystemExit("Could not find Freeplay MusicPlayer field")
if mouse_field not in freeplay_source:
    freeplay_source = freeplay_source.replace(player_field, mouse_field, 1)

update_open = TAB + "override function update(elapsed:Float)" + NL + TAB + "{"
if update_open not in freeplay_source:
    raise SystemExit("Could not find Freeplay update function")
update_start = freeplay_source.index(update_open) + len(update_open)
reset_line = NL + TAB * 2 + "playgroundMouseAccept = false;"
if reset_line not in freeplay_source[update_start:update_start + 120]:
    freeplay_source = freeplay_source[:update_start] + reset_line + freeplay_source[update_start:]

back_anchor = TAB * 2 + "if (controls.BACK)"
back_pos = freeplay_source.index(back_anchor, update_start)
mouse_block = (
    NL + TAB * 2 + "// Browser mouse support: clicking a visible song row starts it."
    + NL + TAB * 2 + "if (!player.playingMusic && grpSongs != null)"
    + NL + TAB * 2 + "{"
    + NL + TAB * 3 + "for (i in 0...grpSongs.members.length)"
    + NL + TAB * 3 + "{"
    + NL + TAB * 4 + "var row:Alphabet = grpSongs.members[i];"
    + NL + TAB * 4 + "if (row != null && row.visible && FlxG.mouse.overlaps(row))"
    + NL + TAB * 4 + "{"
    + NL + TAB * 5 + "if (curSelected != i) changeSelection(i - curSelected, false);"
    + NL + TAB * 5 + "if (FlxG.mouse.justPressed) playgroundMouseAccept = true;"
    + NL + TAB * 4 + "}"
    + NL + TAB * 3 + "}"
    + NL + TAB * 2 + "}"
    + NL + NL
)
if "// Browser mouse support: clicking a visible song row starts it." not in freeplay_source:
    freeplay_source = freeplay_source[:back_pos] + mouse_block + freeplay_source[back_pos:]

accept_old = "else if (controls.ACCEPT && !player.playingMusic)"
accept_new = "else if ((controls.ACCEPT || playgroundMouseAccept) && !player.playingMusic)"
if accept_old in freeplay_source:
    freeplay_source = freeplay_source.replace(accept_old, accept_new, 1)
elif accept_new not in freeplay_source:
    raise SystemExit("Could not find Freeplay ACCEPT branch")

hint_old = 'var leText:String = "Press SPACE to listen to the Song / Press CTRL to open the Gameplay Changers Menu / Press RESET to Reset your Score and Accuracy.";'
hint_new = 'var leText:String = "UP / DOWN: SELECT     ENTER OR CLICK: PLAY     SPACE: PREVIEW";'
if hint_old in freeplay_source:
    freeplay_source = freeplay_source.replace(hint_old, hint_new, 1)

freeplay.write_text(freeplay_source, encoding="utf-8")

# Psych's MusicPlayer assumes playbackRate.split('.')[1] always exists.
# In HTML5, the initial Float can stringify as "1", so guard the decimal part.
music_player = root / "source" / "objects" / "MusicPlayer.hx"
music_player_source = music_player.read_text(encoding="utf-8")
old_playback_rate = """\t\t\tvar playbackRate = Std.string(playbackRate);
\t\t\tif (playbackRate.split('.')[1].length < 2) // Playback rates for like 1.1, 1.2 etc
\t\t\t\tplaybackRate += '0';

\t\t\ttext = playbackRate;"""
new_playback_rate = """\t\t\tvar playbackRateText:String = Std.string(playbackRate);
\t\t\tvar playbackRateParts:Array<String> = playbackRateText.split('.');
\t\t\tif (playbackRateParts.length < 2)
\t\t\t\tplaybackRateText += '.00';
\t\t\telse if (playbackRateParts[1] != null && playbackRateParts[1].length < 2)
\t\t\t\tplaybackRateText += '0';

\t\t\ttext = playbackRateText;"""
if old_playback_rate in music_player_source:
    music_player_source = music_player_source.replace(old_playback_rate, new_playback_rate, 1)
elif new_playback_rate not in music_player_source:
    raise SystemExit("Could not locate MusicPlayer.updatePlaybackTxt decimal parsing")
music_player.write_text(music_player_source, encoding="utf-8")

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
            "import states.MainMenuState;\nimport states.PlaygroundMenuState;",
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
        subtitle.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.CYAN, FlxTextAlign.LEFT);
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
        hint.setFormat(Paths.font("vcr.ttf"), 16, FlxColor.WHITE, FlxTextAlign.CENTER);
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
                MusicBeatState.switchState(new PlaygroundFreeplayState());

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
# PLAY opens Playground's freestyle sandbox, not Psych Freeplay.
menu_source = menu_source.replace(
    "MusicBeatState.switchState(new PlaygroundFreeplayState());",
    "MusicBeatState.switchState(new PlaygroundSandboxState());",
    1
)
menu_file.write_text(menu_source, encoding="utf-8")

# Native Playground sandbox: freeform character animation testing inside Psych Engine.
sandbox_file = root / "source" / "states" / "PlaygroundSandboxState.hx"
sandbox_source = r'''package states;

import backend.BaseStage;
import backend.CoolUtil;
import backend.Paths;
import backend.Song;
import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.util.FlxColor;
import objects.Character;

class PlaygroundSandboxState extends MusicBeatState
{
    private var characterIds:Array<String> = [];
    private var stageIds:Array<String> = ["stage", "spooky", "philly", "limo", "mall", "mallEvil", "school", "schoolEvil", "tank"];
    private var stageLabels:Array<String> = ["WEEK 1 - STAGE", "WEEK 2 - SPOOKY", "WEEK 3 - PHILLY", "WEEK 4 - LIMO", "WEEK 5 - MALL", "WEEK 5 - MALL EVIL", "WEEK 6 - SCHOOL", "WEEK 6 - SCHOOL EVIL", "WEEK 7 - TANK"];
    private var characterIndex:Int = 0;
    private var stageIndex:Int = 0;
    private var player:Character;
    private var activeStage:BaseStage;
    private var stageObjects:Array<FlxBasic> = [];
    private var characterLayerIndex:Int = 0;
    private var characterLabel:FlxText;
    private var stageLabel:FlxText;
    private var actionLabel:FlxText;
    private var singTimer:Float = 0;

    override function create():Void
    {
        super.create();
        FlxG.mouse.visible = true;

        // Load the complete character catalog shipped by Psych Engine.
        characterIds = CoolUtil.coolTextFile(Paths.getSharedPath("data/characterList.txt"));
        characterIds = [for (id in characterIds) if (id != null && id.trim().length > 0) id.trim()];
        if (characterIds.length == 0) characterIds = ["bf", "dad", "gf"];

        // Stage classes read PlayState's song metadata. Supply the built-in tutorial metadata
        // without starting a chart or a PlayState gameplay session.
        try
        {
            PlayState.SONG = Song.loadFromJson("tutorial");
            PlayState.isStoryMode = false;
        }
        catch (error:Dynamic)
        {
            trace("[Playground] Could not read tutorial metadata: " + error);
        }

        drawStage();

        var topBar:FlxSprite = new FlxSprite(0, 0).makeGraphic(FlxG.width, 92, FlxColor.BLACK);
        topBar.alpha = 0.72;
        add(topBar);

        var title:FlxText = new FlxText(28, 13, 560, "FNF PLAYGROUND", 38);
        title.setFormat(Paths.font("vcr.ttf"), 38, FlxColor.WHITE, FlxTextAlign.LEFT);
        add(title);

        var subtitle:FlxText = new FlxText(31, 57, 650, "FREESTYLE SANDBOX  /  PSYCH ENGINE 0.7.3", 15);
        subtitle.setFormat(Paths.font("vcr.ttf"), 15, FlxColor.CYAN, FlxTextAlign.LEFT);
        add(subtitle);

        characterLayerIndex = members.length;
        createSelectedCharacter();

        var sidePanel:FlxSprite = new FlxSprite(24, 125).makeGraphic(350, 370, FlxColor.BLACK);
        sidePanel.alpha = 0.68;
        add(sidePanel);

        characterLabel = new FlxText(45, 150, 310, "", 22);
        characterLabel.setFormat(Paths.font("vcr.ttf"), 22, FlxColor.WHITE, FlxTextAlign.LEFT);
        add(characterLabel);

        stageLabel = new FlxText(45, 190, 310, "", 17);
        stageLabel.setFormat(Paths.font("vcr.ttf"), 17, FlxColor.CYAN, FlxTextAlign.LEFT);
        add(stageLabel);

        var controlsTitle:FlxText = new FlxText(45, 235, 300, "FREESTYLE CONTROLS", 18);
        controlsTitle.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.YELLOW, FlxTextAlign.LEFT);
        add(controlsTitle);

        var controlsText:FlxText = new FlxText(45, 270, 310,
            "ARROWS   SING / ANIMATE\nA / D      CHARACTER\nQ / E      REAL STAGE\nM           IMPORT MOD ZIP\nESC        MAIN MENU", 16);
        controlsText.setFormat(Paths.font("vcr.ttf"), 16, FlxColor.WHITE, FlxTextAlign.LEFT);
        add(controlsText);

        actionLabel = new FlxText(24, FlxG.height - 58, FlxG.width - 48, "PRESS AN ARROW TO FREESTYLE", 19);
        actionLabel.setFormat(Paths.font("vcr.ttf"), 19, FlxColor.WHITE, FlxTextAlign.CENTER);
        add(actionLabel);

        refreshLabels();
    }

    private function createSelectedCharacter():Void
    {
        if (player != null)
        {
            remove(player, true);
            player.destroy();
        }

        var startX:Float = 770;
        var startY:Float = 450;
        var stageData = backend.StageData.getStageFile(stageIds[stageIndex]);
        if (stageData != null && stageData.boyfriend != null && stageData.boyfriend.length > 1)
        {
            startX = stageData.boyfriend[0];
            startY = stageData.boyfriend[1];
        }

        player = new Character(startX, startY, characterIds[characterIndex], true);
        player.dance();
        insert(Std.int(Math.min(characterLayerIndex, members.length)), player);
    }

    private function drawStage():Void
    {
        // Remove only sprites created by the previous native Psych stage class.
        for (object in stageObjects)
        {
            remove(object, true);
            object.destroy();
        }
        stageObjects = [];

        if (activeStage != null)
        {
            stages.remove(activeStage);
            activeStage.destroy();
            activeStage = null;
        }

        if (PlayState.SONG != null)
        {
            PlayState.SONG.stage = stageIds[stageIndex];
            PlayState.SONG.song = stageIds[stageIndex];
            PlayState.SONG.gfVersion = "gf";
        }

        var before:Array<FlxBasic> = members.copy();

        // These are Psych Engine's actual compiled stage implementations and assets,
        // not colored placeholder backgrounds.
        switch (stageIds[stageIndex])
        {
            case "stage": activeStage = new states.stages.StageWeek1();
            case "spooky": activeStage = new states.stages.Spooky();
            case "philly": activeStage = new states.stages.Philly();
            case "limo": activeStage = new states.stages.Limo();
            case "mall": activeStage = new states.stages.Mall();
            case "mallEvil": activeStage = new states.stages.MallEvil();
            case "school": activeStage = new states.stages.School();
            case "schoolEvil": activeStage = new states.stages.SchoolEvil();
            case "tank": activeStage = new states.stages.Tank();
        }

        for (object in members)
        {
            if (before.indexOf(object) < 0)
                stageObjects.push(object);
        }

        // Keep the selected character above the stage sprites and below the editor UI.
        if (player != null)
        {
            remove(player, true);
            insert(Std.int(Math.min(characterLayerIndex, members.length)), player);
        }
    }

    private function refreshLabels():Void
    {
        if (characterLabel != null)
            characterLabel.text = "CHARACTER (" + (characterIndex + 1) + "/" + characterIds.length + "): " + characterIds[characterIndex].toUpperCase();
        if (stageLabel != null)
            stageLabel.text = "STAGE (" + (stageIndex + 1) + "/" + stageIds.length + "): " + stageLabels[stageIndex];
    }

    private function changeCharacter(change:Int):Void
    {
        characterIndex = (characterIndex + change + characterIds.length) % characterIds.length;
        createSelectedCharacter();
        refreshLabels();
        FlxG.sound.play(Paths.sound("scrollMenu"), 0.5);
    }

    private function changeStage(change:Int):Void
    {
        stageIndex = (stageIndex + change + stageIds.length) % stageIds.length;
        drawStage();
        refreshLabels();
        FlxG.sound.play(Paths.sound("scrollMenu"), 0.5);
    }

    private function sing(direction:String):Void
    {
        if (player == null) return;
        player.playAnim("sing" + direction, true);
        singTimer = 0.42;
        actionLabel.text = "PLAYING: SING" + direction.toUpperCase();
    }

    override function update(elapsed:Float):Void
    {
        if (FlxG.keys.justPressed.ESCAPE)
        {
            MusicBeatState.switchState(new PlaygroundMenuState());
            return;
        }

        if (FlxG.keys.justPressed.A) changeCharacter(-1);
        if (FlxG.keys.justPressed.D) changeCharacter(1);
        if (FlxG.keys.justPressed.Q) changeStage(-1);
        if (FlxG.keys.justPressed.E) changeStage(1);

        if (FlxG.keys.justPressed.M)
        {
            PlaygroundModsState.returnToSandbox = true;
            MusicBeatState.switchState(new PlaygroundModsState());
            return;
        }

        if (FlxG.keys.justPressed.LEFT) sing("LEFT");
        if (FlxG.keys.justPressed.DOWN) sing("DOWN");
        if (FlxG.keys.justPressed.UP) sing("UP");
        if (FlxG.keys.justPressed.RIGHT) sing("RIGHT");

        if (singTimer > 0)
        {
            singTimer -= elapsed;
            if (singTimer <= 0 && player != null)
            {
                player.dance();
                actionLabel.text = "PRESS AN ARROW TO FREESTYLE";
            }
        }

        super.update(elapsed);
    }

    override function destroy():Void
    {
        if (activeStage != null)
        {
            stages.remove(activeStage);
            activeStage.destroy();
        }
        super.destroy();
    }
}
'''

sandbox_file.write_text(sandbox_source, encoding="utf-8")

# Retain Psych Freeplay, but turn otherwise opaque browser crashes into a readable error screen.
freeplay_wrapper = root / "source" / "states" / "PlaygroundFreeplayState.hx"
freeplay_wrapper_source = r'''package states;

class PlaygroundFreeplayState extends FreeplayState
{
    private var playgroundFailed:Bool = false;

    override function create():Void
    {
        try
        {
            super.create();
        }
        catch (error:Dynamic)
        {
            showPlaygroundError(error);
        }
    }

    override function update(elapsed:Float):Void
    {
        if (playgroundFailed)
        {
            if (controls.BACK || FlxG.keys.justPressed.ESCAPE)
                MusicBeatState.switchState(new PlaygroundMenuState());
            return;
        }

        try
        {
            super.update(elapsed);
        }
        catch (error:Dynamic)
        {
            showPlaygroundError(error);
        }
    }

    private function showPlaygroundError(error:Dynamic):Void
    {
        if (playgroundFailed) return;
        playgroundFailed = true;
        var message:String = Std.string(error) + "\nPhase: " + FreeplayState.playgroundDebugStage + "\n\n" + haxe.CallStack.toString(haxe.CallStack.exceptionStack(true));
        trace("[Playground Freeplay error] " + message);

        var shade:FlxSprite = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
        shade.alpha = 0.92;
        add(shade);

        var title:FlxText = new FlxText(45, 65, FlxG.width - 90, "FREEPLAY COULD NOT START", 34);
        title.setFormat(Paths.font("vcr.ttf"), 34, FlxColor.RED, CENTER);
        add(title);

        var detail:FlxText = new FlxText(70, 160, FlxG.width - 140, message, 20);
        detail.setFormat(Paths.font("vcr.ttf"), 20, FlxColor.WHITE, FlxTextAlign.CENTER);
        detail.borderStyle = FlxTextBorderStyle.OUTLINE;
        detail.borderColor = FlxColor.BLACK;
        detail.borderSize = 2;
        add(detail);

        var hint:FlxText = new FlxText(0, FlxG.height - 80, FlxG.width, "ESC — BACK TO PLAYGROUND MENU", 18);
        hint.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.CYAN, CENTER);
        add(hint);
    }
}
'''
freeplay_wrapper.write_text(freeplay_wrapper_source, encoding="utf-8")

# Browser-side ZIP importer and asset cache for Playground mods.
mod_store = root / "source" / "backend" / "PlaygroundModStore.hx"
mod_store_source = r'''package backend;

import haxe.crypto.Base64;
import haxe.ds.StringMap;
import haxe.io.Bytes;
import haxe.io.BytesInput;
import haxe.zip.Reader;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;

class PlaygroundModStore
{
    public static var activeModName:String = "";
    public static var characterIds:Array<String> = [];
    private static var files:StringMap<Bytes> = new StringMap<Bytes>();
    private static var graphics:StringMap<FlxGraphic> = new StringMap<FlxGraphic>();

    public static function getText(path:String):String
    {
        var normalized = normalizePath(path);
        if (normalized == null) return null;
        var data = files.get(normalized);
        if (data == null) data = files.get(normalized.toLowerCase());
        return data == null ? null : data.toString();
    }

    public static function getGraphic(key:String):FlxGraphic
    {
        var path = key;
        if (!path.startsWith("images/")) path = "images/" + path;
        if (!path.toLowerCase().endsWith(".png")) path += ".png";
        var result = graphics.get(path);
        if (result == null) result = graphics.get(path.toLowerCase());
        return result;
    }

    public static function importZip(bytes:Bytes, name:String, callback:Bool->String->Void):Void
    {
        if (bytes == null || bytes.length < 4)
        {
            callback(false, "The selected file is empty or is not a ZIP archive.");
            return;
        }

        parseArchive(bytes, function(success:Bool, message:String)
        {
            if (!success)
            {
                callback(false, message);
                return;
            }
            activeModName = name;
            saveArchive(bytes, name, callback);
        });
    }

    public static function loadStored(callback:Bool->String->Void):Void
    {
        #if js
        openDatabase(function(db:Dynamic)
        {
            var tx:Dynamic = db.transaction(["mods"], "readonly");
            var request:Dynamic = tx.objectStore("mods").get("active");
            request.onsuccess = function(_)
            {
                var record:Dynamic = request.result;
                if (record == null)
                {
                    callback(false, "No imported mod.");
                    return;
                }
                activeModName = Reflect.field(record, "name");
                try
                {
                    var archive:String = Reflect.field(record, "archive");
                    parseArchive(Base64.decode(archive), callback);
                }
                catch (error:Dynamic)
                {
                    callback(false, "Could not restore the imported ZIP: " + Std.string(error));
                }
            };
            request.onerror = function(_) callback(false, "Could not read the saved mod.");
        }, function(error:String) callback(false, error));
        #else
        callback(false, "ZIP storage is only available in the HTML5 build.");
        #end
    }

    public static function clearStored(callback:Bool->String->Void):Void
    {
        #if js
        openDatabase(function(db:Dynamic)
        {
            var tx:Dynamic = db.transaction(["mods"], "readwrite");
            tx.objectStore("mods").delete("active");
            tx.oncomplete = function(_)
            {
                activeModName = "";
                characterIds = [];
                files = new StringMap<Bytes>();
                graphics = new StringMap<FlxGraphic>();
                callback(true, "Imported mod removed.");
            };
            tx.onerror = function(_) callback(false, "Could not remove the saved mod.");
        }, function(error:String) callback(false, error));
        #else
        callback(false, "ZIP storage is only available in the HTML5 build.");
        #end
    }

    private static function saveArchive(bytes:Bytes, name:String, callback:Bool->String->Void):Void
    {
        #if js
        openDatabase(function(db:Dynamic)
        {
            var tx:Dynamic = db.transaction(["mods"], "readwrite");
            tx.objectStore("mods").put({name: name, archive: Base64.encode(bytes)}, "active");
            tx.oncomplete = function(_) callback(true, "Mod imported and saved.");
            tx.onerror = function(_) callback(false, "Browser storage could not save this ZIP.");
        }, function(error:String) callback(false, error));
        #else
        callback(false, "ZIP importing is only available in the HTML5 build.");
        #end
    }

    #if js
    private static function openDatabase(onReady:Dynamic->Void, onError:String->Void):Void
    {
        try
        {
            var factory:Dynamic = untyped js.Browser.window.indexedDB;
            if (factory == null)
            {
                onError("This browser does not support IndexedDB.");
                return;
            }
            var request:Dynamic = factory.open("FNFPlaygroundMods", 1);
            request.onupgradeneeded = function(_)
            {
                var db:Dynamic = request.result;
                if (!db.objectStoreNames.contains("mods")) db.createObjectStore("mods");
            };
            request.onsuccess = function(_) onReady(request.result);
            request.onerror = function(_) onError("Could not open browser mod storage.");
        }
        catch (error:Dynamic)
        {
            onError("Browser storage error: " + Std.string(error));
        }
    }
    #end

    private static function normalizePath(raw:String):String
    {
        if (raw == null) return null;
        var path = raw.split("\\").join("/");
        while (path.startsWith("/")) path = path.substr(1);
        var pieces = path.split("/");
        for (piece in pieces)
            if (piece == "..") return null;

        var roots = ["characters", "images", "stages", "data", "songs", "weeks", "fonts"];
        var first = -1;
        for (i in 0...pieces.length)
        {
            if (roots.indexOf(pieces[i].toLowerCase()) >= 0)
            {
                first = i;
                break;
            }
        }
        if (first < 0) return null;
        return pieces.slice(first).join("/");
    }

    private static function parseArchive(bytes:Bytes, callback:Bool->String->Void):Void
    {
        try
        {
            files = new StringMap<Bytes>();
            graphics = new StringMap<FlxGraphic>();
            characterIds = [];

            var entries = Reader.readZip(new BytesInput(bytes));
            for (entry in entries)
            {
                if (entry.fileName == null || entry.fileName.endsWith("/") || entry.data == null) continue;
                var path = normalizePath(entry.fileName);
                if (path == null) continue;

                var data:Bytes = entry.data;
                if (entry.compressed) data = haxe.zip.Uncompress.run(data);
                files.set(path, data);
                files.set(path.toLowerCase(), data);

                var lower = path.toLowerCase();
                if (lower.startsWith("characters/") && lower.endsWith(".json"))
                {
                    var id = path.substring("characters/".length, path.length - 5);
                    if (id.indexOf("/") < 0 && characterIds.indexOf(id) < 0)
                        characterIds.push(id);
                }
            }

            if (characterIds.length == 0)
            {
                callback(false, "No characters/*.json files were found. Choose a Psych Engine mod ZIP.");
                return;
            }
            preloadCharacterImages(callback);
        }
        catch (error:Dynamic)
        {
            callback(false, "Could not extract this ZIP: " + Std.string(error));
        }
    }

    private static function preloadCharacterImages(callback:Bool->String->Void):Void
    {
        var needed:StringMap<Bool> = new StringMap<Bool>();
        for (id in characterIds)
        {
            var jsonText = getText("characters/" + id + ".json");
            if (jsonText == null) continue;
            try
            {
                var json:Dynamic = haxe.Json.parse(jsonText);
                var image:String = Reflect.field(json, "image");
                if (image != null && image.length > 0)
                {
                    var path = image;
                    if (!path.startsWith("images/")) path = "images/" + path;
                    if (!path.toLowerCase().endsWith(".png")) path += ".png";
                    if (files.exists(path)) needed.set(path, true);
                    else if (files.exists(path.toLowerCase())) needed.set(path.toLowerCase(), true);
                }
            }
            catch (error:Dynamic)
            {
                trace("[Playground Mods] Invalid character JSON " + id + ": " + error);
            }
        }

        var paths:Array<String> = [for (path in needed.keys()) path];
        if (paths.length == 0)
        {
            callback(true, "Imported " + characterIds.length + " character definitions; atlas PNGs were not found.");
            return;
        }

        var pending:Int = paths.length;
        var failed:Int = 0;
        for (path in paths)
        {
            var png:Bytes = files.get(path);
            if (png == null) png = files.get(path.toLowerCase());
            BitmapData.loadFromBytes(png).onComplete(function(bitmap:BitmapData)
            {
                if (bitmap != null)
                {
                    var graphic = FlxGraphic.fromBitmapData(bitmap, false, "playground-mod:" + path);
                    graphics.set(path, graphic);
                    graphics.set(path.toLowerCase(), graphic);
                }
                else failed++;
                pending--;
                if (pending == 0)
                    callback(true, "Imported " + characterIds.length + " characters; " + (paths.length - failed) + " atlases loaded.");
            }).onError(function(error:Dynamic)
            {
                failed++;
                pending--;
                if (pending == 0)
                    callback(true, "Imported " + characterIds.length + " characters; " + (paths.length - failed) + " atlases loaded.");
            });
        }
    }
}
'''
mod_store.write_text(mod_store_source, encoding="utf-8")

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
