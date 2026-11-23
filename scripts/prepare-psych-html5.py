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
import backend.ClientPrefs;
import backend.CoolUtil;
import backend.Paths;
import backend.PlaygroundModStore;
import backend.Song;
import backend.StageData;
import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.FlxCamera.FlxCameraFollowStyle;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.util.FlxColor;
import objects.Character;

class PlaygroundSandboxState extends MusicBeatState
{
    private var characterIds:Array<String> = [];
    private var stageIds:Array<String> = ["stage", "spooky", "philly", "limo", "mall", "mallEvil", "school", "schoolEvil", "tank"];
    private var stageDirectories:Array<String> = ["week1", "week2", "week3", "week4", "week5", "week5", "week6", "week6", "week7"];
    private var stageLabels:Array<String> = ["WEEK 1 - STAGE", "WEEK 2 - SPOOKY", "WEEK 3 - PHILLY", "WEEK 4 - LIMO", "WEEK 5 - MALL", "WEEK 5 - MALL EVIL", "WEEK 6 - SCHOOL", "WEEK 6 - SCHOOL EVIL", "WEEK 7 - TANK"];

    private var characterIndexP1:Int = 0;
    private var characterIndexP2:Int = 0;
    private var stageIndex:Int = 0;

    private var playerOne:Character;
    private var playerTwo:Character;
    private var playerOneSingTimer:Float = 0;
    private var playerTwoSingTimer:Float = 0;
    private var cameraTarget:FlxObject;
    private var activeStage:BaseStage;
    private var stageObjects:Array<FlxBasic> = [];

    private var playerOneLabel:FlxText;
    private var playerTwoLabel:FlxText;
    private var stageLabel:FlxText;
    private var actionLabel:FlxText;

    private var previousAssetDirectory:String = null;

    override function create():Void
    {
        super.create();
        FlxG.mouse.visible = true;
        previousAssetDirectory = Paths.currentLevel;

        var loading:FlxText = new FlxText(0, FlxG.height * 0.45, FlxG.width, "LOADING PLAYGROUND...", 24);
        loading.setFormat(Paths.font("vcr.ttf"), 24, FlxColor.WHITE, FlxTextAlign.CENTER);
        add(loading);

        PlaygroundModStore.loadStored(function(success:Bool, message:String)
        {
            remove(loading, true);
            loading.destroy();
            if (!success && message != "No imported mod.")
                trace("[Playground] Mod restore: " + message);
            buildPlayground();
        });
    }

    private function buildPlayground():Void
    {
        characterIds = CoolUtil.coolTextFile(Paths.getSharedPath("data/characterList.txt"));
        if (characterIds == null) characterIds = [];
        characterIds = [for (id in characterIds) if (id != null && id.trim().length > 0) id.trim()];

        for (modCharacter in PlaygroundModStore.characterIds)
            if (characterIds.indexOf(modCharacter) < 0) characterIds.push(modCharacter);

        if (characterIds.indexOf("bf") < 0) characterIds.unshift("bf");
        if (characterIds.indexOf("dad") < 0) characterIds.push("dad");

        characterIndexP1 = characterIds.indexOf("bf");
        characterIndexP2 = characterIds.indexOf("dad");
        if (characterIndexP1 < 0) characterIndexP1 = 0;
        if (characterIndexP2 < 0) characterIndexP2 = 0;

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

        cameraTarget = new FlxObject(0, 0, 1, 1);
        add(cameraTarget);
        createPlayers();

        var topBar:FlxSprite = new FlxSprite(0, 0).makeGraphic(FlxG.width, 82, FlxColor.BLACK);
        topBar.alpha = 0.68;
        topBar.scrollFactor.set(0, 0);
        add(topBar);

        var title:FlxText = new FlxText(28, 18, 560, "FNF PLAYGROUND", 36);
        title.setFormat(Paths.font("vcr.ttf"), 36, FlxColor.WHITE, FlxTextAlign.LEFT);
        title.scrollFactor.set(0, 0);
        add(title);

        var infoStart:Float = FlxG.width * 0.37;

        playerOneLabel = new FlxText(infoStart, 20, FlxG.width * 0.18, "", 15);
        playerOneLabel.setFormat(Paths.font("vcr.ttf"), 15, FlxColor.CYAN, FlxTextAlign.LEFT);
        playerOneLabel.scrollFactor.set(0, 0);
        add(playerOneLabel);

        playerTwoLabel = new FlxText(FlxG.width * 0.56, 20, FlxG.width * 0.18, "", 15);
        playerTwoLabel.setFormat(Paths.font("vcr.ttf"), 15, FlxColor.LIME, FlxTextAlign.LEFT);
        playerTwoLabel.scrollFactor.set(0, 0);
        add(playerTwoLabel);

        stageLabel = new FlxText(FlxG.width * 0.75, 20, FlxG.width * 0.23, "", 14);
        stageLabel.setFormat(Paths.font("vcr.ttf"), 14, FlxColor.WHITE, FlxTextAlign.LEFT);
        stageLabel.scrollFactor.set(0, 0);
        add(stageLabel);

        var controlsText:FlxText = new FlxText(24, FlxG.height - 78, FlxG.width - 48,
            "P1: ARROWS  |  P2: W A S D  |  F/G: P1 CHARACTER  |  U/I: P2 CHARACTER  |  Q/E: STAGE  |  M: MODS", 12);
        controlsText.setFormat(Paths.font("vcr.ttf"), 12, FlxColor.WHITE, FlxTextAlign.CENTER);
        controlsText.alpha = 0.88;
        controlsText.scrollFactor.set(0, 0);
        add(controlsText);

        actionLabel = new FlxText(24, FlxG.height - 48, FlxG.width - 48, "P1: ARROWS     P2: W A S D", 18);
        actionLabel.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.WHITE, FlxTextAlign.CENTER);
        actionLabel.scrollFactor.set(0, 0);
        add(actionLabel);

        refreshLabels();
        focusCamera(true);
    }

    private function stageFile():Dynamic
    {
        return StageData.getStageFile(stageIds[stageIndex]);
    }

    private function characterPosition(isPlayerOne:Bool):Array<Float>
    {
        var data = stageFile();
        if (data != null)
        {
            var coords:Array<Dynamic> = isPlayerOne ? data.boyfriend : data.opponent;
            if (coords != null && coords.length > 1)
                return [coords[0], coords[1]];
        }
        return isPlayerOne ? [770, 100] : [100, 100];
    }

    private function createPlayers():Void
    {
        if (playerOne != null)
        {
            remove(playerOne, true);
            playerOne.destroy();
        }
        if (playerTwo != null)
        {
            remove(playerTwo, true);
            playerTwo.destroy();
        }

        var p1Pos = characterPosition(true);
        var p2Pos = characterPosition(false);
        playerOne = new Character(p1Pos[0], p1Pos[1], characterIds[characterIndexP1], true);
        playerTwo = new Character(p2Pos[0], p2Pos[1], characterIds[characterIndexP2], false);

        // This sandbox has no running Conductor/song clock. Keep both actors as
        // players and use a local elapsed-time timer instead of Character's
        // beat-based opponent timeout, which can expire almost immediately here.
        playerOne.isPlayer = true;
        playerTwo.isPlayer = true;
        playerOneSingTimer = 0;
        playerTwoSingTimer = 0;
        playerOne.holdTimer = 0;
        playerTwo.holdTimer = 0;
        playerOne.dance();
        playerTwo.dance();

        reorderMainLayers();
        focusCamera(true);
    }

    private function reorderMainLayers():Void
    {
        var nextLayer:Int = stageObjects.length;
        if (cameraTarget != null)
        {
            remove(cameraTarget, true);
            insert(Std.int(Math.min(nextLayer, members.length)), cameraTarget);
            nextLayer++;
        }
        if (playerOne != null)
        {
            remove(playerOne, true);
            insert(Std.int(Math.min(nextLayer, members.length)), playerOne);
            nextLayer++;
        }
        if (playerTwo != null)
        {
            remove(playerTwo, true);
            insert(Std.int(Math.min(nextLayer, members.length)), playerTwo);
        }
    }

    private function drawStage():Void
    {
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

        if (PlayState.SONG == null)
        {
            try PlayState.SONG = Song.loadFromJson("tutorial")
            catch (error:Dynamic) trace("[Playground] Song metadata unavailable: " + error);
        }

        var data = stageFile();
        var assetDirectory:String = stageDirectories[stageIndex];
        if (data != null && data.directory != null && data.directory.length > 0)
            assetDirectory = data.directory;

        Paths.setCurrentLevel(assetDirectory);
        PlayState.curStage = stageIds[stageIndex];

        if (PlayState.SONG != null)
        {
            PlayState.SONG.stage = stageIds[stageIndex];
            PlayState.SONG.song = "Tutorial";
            PlayState.SONG.gfVersion = "gf";
        }

        var before:Array<FlxBasic> = members.copy();
        try
        {
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
        }
        catch (error:Dynamic)
        {
            trace("[Playground] Stage " + stageIds[stageIndex] + " failed: " + error);
            activeStage = null;
        }

        for (object in members)
            if (before.indexOf(object) < 0)
                stageObjects.push(object);

        var layer:Int = 0;
        for (object in stageObjects)
        {
            remove(object, true);
            insert(layer, object);
            layer++;
        }

        reorderMainLayers();
        if (cameraTarget != null)
            focusCamera(true);
    }

    private function offsetValue(values:Array<Float>, index:Int):Float
    {
        return values != null && values.length > index ? values[index] : 0;
    }

    private function focusCamera(onPlayerOne:Bool):Void
    {
        if (cameraTarget == null) return;
        var actor:Character = onPlayerOne ? playerOne : playerTwo;
        if (actor == null) return;

        var data = stageFile();
        var zoom:Float = (data != null && data.defaultZoom != null && data.defaultZoom > 0) ? data.defaultZoom : 0.9;
        FlxG.camera.zoom = zoom;

        var midpoint = actor.getMidpoint();
        if (onPlayerOne)
        {
            cameraTarget.setPosition(midpoint.x - 100, midpoint.y - 100);
            cameraTarget.x -= offsetValue(actor.cameraPosition, 0) - offsetValue(data == null ? null : data.camera_boyfriend, 0);
            cameraTarget.y += offsetValue(actor.cameraPosition, 1) + offsetValue(data == null ? null : data.camera_boyfriend, 1);
        }
        else
        {
            cameraTarget.setPosition(midpoint.x + 150, midpoint.y - 100);
            cameraTarget.x += offsetValue(actor.cameraPosition, 0) + offsetValue(data == null ? null : data.camera_opponent, 0);
            cameraTarget.y += offsetValue(actor.cameraPosition, 1) + offsetValue(data == null ? null : data.camera_opponent, 1);
        }

        // Match Psych Engine's PlayState camera setup: lock onto a fixed target
        // with zero lerp, so focus changes snap instead of accumulating drift.
        FlxG.camera.follow(cameraTarget, FlxCameraFollowStyle.LOCKON, 0);
    }

    private function refreshLabels():Void
    {
        if (playerOneLabel != null && characterIds.length > 0)
            playerOneLabel.text = "P1: " + characterIds[characterIndexP1].toUpperCase();
        if (playerTwoLabel != null && characterIds.length > 0)
            playerTwoLabel.text = "P2: " + characterIds[characterIndexP2].toUpperCase();
        if (stageLabel != null)
            stageLabel.text = "STAGE: " + stageLabels[stageIndex];
    }

    private function changePlayerCharacter(isPlayerOne:Bool, change:Int):Void
    {
        if (characterIds.length == 0) return;
        if (isPlayerOne)
            characterIndexP1 = (characterIndexP1 + change + characterIds.length) % characterIds.length;
        else
            characterIndexP2 = (characterIndexP2 + change + characterIds.length) % characterIds.length;

        createPlayers();
        refreshLabels();
        FlxG.sound.play(Paths.sound("scrollMenu"), 0.5);
    }

    private function changeStage(change:Int):Void
    {
        stageIndex = (stageIndex + change + stageIds.length) % stageIds.length;
        drawStage();

        var p1Pos = characterPosition(true);
        var p2Pos = characterPosition(false);
        if (playerOne != null) playerOne.setPosition(p1Pos[0], p1Pos[1]);
        if (playerTwo != null) playerTwo.setPosition(p2Pos[0], p2Pos[1]);

        focusCamera(true);
        refreshLabels();
        FlxG.sound.play(Paths.sound("scrollMenu"), 0.5);
    }

    private function singPlayer(isPlayerOne:Bool, direction:String):Void
    {
        var actor:Character = isPlayerOne ? playerOne : playerTwo;
        if (actor == null) return;
        actor.holdTimer = 0;
        if (isPlayerOne) playerOneSingTimer = 0.22;
        else playerTwoSingTimer = 0.22;
        actor.playAnim("sing" + direction, true);

        actionLabel.text = (isPlayerOne ? "PLAYER 1" : "PLAYER 2") + " / SING " + direction;
        focusCamera(isPlayerOne);
    }

    private function boundJustPressed(action:String):Bool
    {
        return controls != null && controls.justPressed(action);
    }

    override function update(elapsed:Float):Void
    {
        if (FlxG.keys.justPressed.ESCAPE)
        {
            MusicBeatState.switchState(new PlaygroundMenuState());
            return;
        }

        if (FlxG.keys.justPressed.F) changePlayerCharacter(true, -1);
        if (FlxG.keys.justPressed.G) changePlayerCharacter(true, 1);
        if (FlxG.keys.justPressed.U) changePlayerCharacter(false, -1);
        if (FlxG.keys.justPressed.I) changePlayerCharacter(false, 1);
        if (FlxG.keys.justPressed.Q) changeStage(-1);
        if (FlxG.keys.justPressed.E) changeStage(1);

        if (FlxG.keys.justPressed.M)
        {
            PlaygroundModsState.returnToSandbox = true;
            MusicBeatState.switchState(new PlaygroundModsState());
            return;
        }

        if (boundJustPressed("pg_p1_note_left")) singPlayer(true, "LEFT");
        if (boundJustPressed("pg_p1_note_down")) singPlayer(true, "DOWN");
        if (boundJustPressed("pg_p1_note_up")) singPlayer(true, "UP");
        if (boundJustPressed("pg_p1_note_right")) singPlayer(true, "RIGHT");

        if (boundJustPressed("pg_p2_note_left")) singPlayer(false, "LEFT");
        if (boundJustPressed("pg_p2_note_down")) singPlayer(false, "DOWN");
        if (boundJustPressed("pg_p2_note_up")) singPlayer(false, "UP");
        if (boundJustPressed("pg_p2_note_right")) singPlayer(false, "RIGHT");

        // Return to idle after a short fixed hold. This is independent of BPM,
        // Conductor.stepCrochet, and whether a song is currently playing.
        if (playerOneSingTimer > 0)
        {
            playerOneSingTimer -= elapsed;
            if (playerOneSingTimer <= 0 && playerOne != null) playerOne.dance();
        }
        if (playerTwoSingTimer > 0)
        {
            playerTwoSingTimer -= elapsed;
            if (playerTwoSingTimer <= 0 && playerTwo != null) playerTwo.dance();
        }

        super.update(elapsed);
    }

    override function destroy():Void
    {
        if (activeStage != null)
        {
            stages.remove(activeStage);
            activeStage.destroy();
            activeStage = null;
        }
        stageObjects = [];
        Paths.currentLevel = previousAssetDirectory;
        super.destroy();
    }
}

'''

sandbox_file.write_text(sandbox_source, encoding="utf-8")


# Add independently rebindable Playground controls to Psych Engine's native Controls menu.
client_prefs = root / "source" / "backend" / "ClientPrefs.hx"
client_prefs_source = client_prefs.read_text(encoding="utf-8")
keyboard_anchor = "\t\t'note_right'\t=> [D, RIGHT],"
keyboard_add = """\t\t'note_right'\t=> [D, RIGHT],

\t\t'pg_p1_note_left'\t=> [LEFT, NONE],
\t\t'pg_p1_note_down'\t=> [DOWN, NONE],
\t\t'pg_p1_note_up'\t\t=> [UP, NONE],
\t\t'pg_p1_note_right'\t=> [RIGHT, NONE],
\t\t'pg_p2_note_left'\t=> [A, NONE],
\t\t'pg_p2_note_down'\t=> [S, NONE],
\t\t'pg_p2_note_up'\t\t=> [W, NONE],
\t\t'pg_p2_note_right'\t=> [D, NONE],"""
if "pg_p1_note_left" not in client_prefs_source:
    if keyboard_anchor not in client_prefs_source:
        raise SystemExit("Could not locate ClientPrefs keyboard note bindings")
    client_prefs_source = client_prefs_source.replace(keyboard_anchor, keyboard_add, 1)

gamepad_anchor = "\t\t'note_right'\t=> [DPAD_RIGHT, B],"
gamepad_add = """\t\t'note_right'\t=> [DPAD_RIGHT, B],

\t\t'pg_p1_note_left'\t=> [DPAD_LEFT, NONE],
\t\t'pg_p1_note_down'\t=> [DPAD_DOWN, NONE],
\t\t'pg_p1_note_up'\t\t=> [DPAD_UP, NONE],
\t\t'pg_p1_note_right'\t=> [DPAD_RIGHT, NONE],
\t\t'pg_p2_note_left'\t=> [X, NONE],
\t\t'pg_p2_note_down'\t=> [A, NONE],
\t\t'pg_p2_note_up'\t\t=> [Y, NONE],
\t\t'pg_p2_note_right'\t=> [B, NONE],"""
if "pg_p1_note_left" in client_prefs_source and gamepad_anchor in client_prefs_source and "'pg_p1_note_left'\t=> [DPAD_LEFT, NONE]" not in client_prefs_source:
    client_prefs_source = client_prefs_source.replace(gamepad_anchor, gamepad_add, 1)
client_prefs.write_text(client_prefs_source, encoding="utf-8")

controls_file = root / "source" / "options" / "ControlsSubState.hx"
controls_source = controls_file.read_text(encoding="utf-8")
controls_anchor = "\t\t[true, 'NOTES'],"
controls_add = """\t\t[true, 'NOTES'],
\t\t[true, 'PLAYGROUND / PLAYER 1'],
\t\t[true, 'Left', 'pg_p1_note_left', 'Player 1 Left'],
\t\t[true, 'Down', 'pg_p1_note_down', 'Player 1 Down'],
\t\t[true, 'Up', 'pg_p1_note_up', 'Player 1 Up'],
\t\t[true, 'Right', 'pg_p1_note_right', 'Player 1 Right'],
\t\t[true, 'PLAYGROUND / PLAYER 2'],
\t\t[true, 'Left', 'pg_p2_note_left', 'Player 2 Left'],
\t\t[true, 'Down', 'pg_p2_note_down', 'Player 2 Down'],
\t\t[true, 'Up', 'pg_p2_note_up', 'Player 2 Up'],
\t\t[true, 'Right', 'pg_p2_note_right', 'Player 2 Right'],"""
if "pg_p1_note_left" not in controls_source:
    if controls_anchor not in controls_source:
        raise SystemExit("Could not locate ControlsSubState note section")
    controls_source = controls_source.replace(controls_anchor, controls_add, 1)
controls_file.write_text(controls_source, encoding="utf-8")

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
import haxe.Timer;
import haxe.io.Bytes;
import haxe.io.BytesInput;
import haxe.zip.Reader;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;
import openfl.utils.ByteArray;

class PlaygroundModStore
{
    public static var activeModName:String = "";
    public static var characterIds:Array<String> = [];
    private static var files:StringMap<Bytes> = new StringMap<Bytes>();
    private static var graphics:StringMap<FlxGraphic> = new StringMap<FlxGraphic>();

    private static inline var MAX_ARCHIVE_BYTES:Int = 52428800;
    private static inline var MAX_ENTRIES:Int = 2500;
    private static inline var MAX_CHARACTER_JSON_BYTES:Int = 8388608;
    private static inline var MAX_SELECTED_ASSET_BYTES:Int = 100663296;
    private static inline var MAX_DECODED_PIXELS:Int = 18000000;

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
        if (bytes.length > MAX_ARCHIVE_BYTES)
        {
            callback(false, "This ZIP is larger than the 50 MB browser import limit.");
            return;
        }

        // Validate character JSON only. PNGs are decoded after the page reload.
        parseArchive(bytes, function(success:Bool, message:String)
        {
            if (!success)
            {
                callback(false, message);
                return;
            }
            activeModName = name;
            saveArchive(bytes, name, callback);
        }, false);
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
                    var stored:Dynamic = Reflect.field(record, "archive");
                    var archiveBytes:Bytes;
                    // Legacy saves used Base64. New saves use the typed byte array.
                    if (Std.isOfType(stored, String))
                        archiveBytes = Base64.decode(cast stored);
                    else
                        archiveBytes = Bytes.ofData(cast stored);

                    if (archiveBytes.length > MAX_ARCHIVE_BYTES)
                    {
                        callback(false, "The saved ZIP exceeds the browser import limit.");
                        return;
                    }
                    parseArchive(archiveBytes, callback, true);
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
            tx.objectStore("mods").put({name: name, archive: bytes.getData()}, "active");
            tx.oncomplete = function(_) callback(true, "Mod saved. The Playground will reload once.");
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
        var path = raw.split(String.fromCharCode(92)).join("/");
        while (path.startsWith("/")) path = path.substr(1);
        var pieces = path.split("/");
        for (piece in pieces)
            if (piece == "..") return null;

        var roots = ["characters", "images"];
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

    private static function inflateEntry(entry:Dynamic):Bytes
    {
        var data:Bytes = cast entry.data;
        if (data == null) throw "ZIP entry has no data.";
        var size:Int = entry.fileSize;
        if (size < 0 || size > MAX_SELECTED_ASSET_BYTES)
            throw "ZIP entry is larger than the allowed extraction limit.";

        if (entry.compressed)
        {
            var inflater = new haxe.zip.InflateImpl(new BytesInput(data), false, false);
            var uncompressed = Bytes.alloc(size);
            var written = inflater.readBytes(uncompressed, 0, size);
            if (written != size)
                throw "Incomplete ZIP entry: " + entry.fileName;
            return uncompressed;
        }
        if (data.length != size)
            throw "Invalid ZIP entry length: " + entry.fileName;
        return data;
    }

    private static function atlasBase(image:String):String
    {
        if (image == null || image.length == 0) return null;
        var base = image.split(String.fromCharCode(92)).join("/");
        while (base.startsWith("/")) base = base.substr(1);
        if (base.startsWith("images/")) base = base.substr("images/".length);

        var lower = base.toLowerCase();
        for (extension in [".png", ".xml", ".txt", ".json"])
        {
            if (lower.endsWith(extension))
            {
                base = base.substr(0, base.length - extension.length);
                break;
            }
        }
        return normalizePath("images/" + base);
    }

    private static function parseArchive(bytes:Bytes, callback:Bool->String->Void, preloadImages:Bool = true):Void
    {
        try
        {
            if (bytes == null || bytes.length < 4 || bytes.length > MAX_ARCHIVE_BYTES)
                throw "ZIP is empty or exceeds the 50 MB import limit.";

            files = new StringMap<Bytes>();
            graphics = new StringMap<FlxGraphic>();
            characterIds = [];

            // Keep compressed entries in memory, but only extract character JSON
            // and graphics that those characters actually reference.
            var entries:Array<Dynamic> = [for (entry in Reader.readZip(new BytesInput(bytes))) entry];
            if (entries.length > MAX_ENTRIES)
                throw "This ZIP contains too many files (maximum 2500).";

            var available:StringMap<Dynamic> = new StringMap<Dynamic>();
            var characterEntries:Array<Dynamic> = [];
            for (entry in entries)
            {
                if (entry.fileName == null || entry.fileName.endsWith("/") || entry.data == null) continue;
                var path = normalizePath(entry.fileName);
                if (path == null) continue;
                available.set(path.toLowerCase(), {path: path, entry: entry});

                var lower = path.toLowerCase();
                if (lower.startsWith("characters/") && lower.endsWith(".json"))
                {
                    var id = path.substring("characters/".length, path.length - 5);
                    if (id.indexOf("/") < 0 && characterIds.indexOf(id) < 0)
                    {
                        characterIds.push(id);
                        characterEntries.push({path: path, entry: entry});
                    }
                }
            }

            if (characterEntries.length == 0)
            {
                callback(false, "No characters/*.json files were found. Choose a Psych Engine character mod ZIP.");
                return;
            }

            var wanted:StringMap<Bool> = new StringMap<Bool>();
            var cursor:Int = 0;
            var jsonBytes:Int = 0;
            var parseJsonChunk:Void->Void = null;
            parseJsonChunk = function():Void
            {
                try
                {
                    var stop = Std.int(Math.min(cursor + 6, characterEntries.length));
                    while (cursor < stop)
                    {
                        var record:Dynamic = characterEntries[cursor++];
                        var path:String = record.path;
                        var entry:Dynamic = record.entry;
                        var size:Int = entry.fileSize;
                        if (size < 0 || size > MAX_CHARACTER_JSON_BYTES)
                            throw "A character JSON is larger than the 8 MB limit.";
                        jsonBytes += size;
                        if (jsonBytes > MAX_CHARACTER_JSON_BYTES)
                            throw "Character JSON files exceed the 8 MB total limit.";

                        var data = inflateEntry(entry);
                        files.set(path, data);
                        files.set(path.toLowerCase(), data);

                        try
                        {
                            var json:Dynamic = haxe.Json.parse(data.toString());
                            var image:String = Reflect.field(json, "image");
                            var base = atlasBase(image);
                            if (base != null)
                            {
                                for (extension in [".png", ".xml", ".txt", ".json"])
                                    wanted.set((base + extension).toLowerCase(), true);
                            }
                        }
                        catch (jsonError:Dynamic)
                        {
                            trace("[Playground Mods] Invalid character JSON " + path + ": " + jsonError);
                        }
                    }

                    if (cursor < characterEntries.length)
                    {
                        Timer.delay(parseJsonChunk, 1);
                        return;
                    }

                    var assetRecords:Array<Dynamic> = [];
                    var totalAssetBytes:Int = 0;
                    for (path in wanted.keys())
                    {
                        var record:Dynamic = available.get(path);
                        if (record == null) continue;
                        var entry:Dynamic = record.entry;
                        var size:Int = entry.fileSize;
                        if (size < 0 || size > MAX_SELECTED_ASSET_BYTES)
                            throw "A referenced character atlas is too large.";
                        totalAssetBytes += size;
                        if (totalAssetBytes > MAX_SELECTED_ASSET_BYTES)
                            throw "Referenced character atlases exceed the 96 MB extraction limit.";
                        assetRecords.push(record);
                    }

                    if (!preloadImages)
                    {
                        callback(true, "Validated " + characterIds.length + " character JSON files. Assets will load after the page reload.");
                        return;
                    }

                    // Decode one PNG at a time instead of launching all image decoders together.
                    var assetIndex:Int = 0;
                    var decodedPixels:Int = 0;
                    var failedAtlases:Int = 0;
                    var loadNextAsset:Void->Void = null;
                    loadNextAsset = function():Void
                    {
                        if (assetIndex >= assetRecords.length)
                        {
                            callback(true, "Loaded " + characterIds.length + " characters; " + failedAtlases + " atlas files could not be decoded.");
                            return;
                        }

                        var record:Dynamic = assetRecords[assetIndex++];
                        var path:String = record.path;
                        var entry:Dynamic = record.entry;
                        try
                        {
                            var data = inflateEntry(entry);
                            if (path.toLowerCase().endsWith(".png"))
                            {
                                BitmapData.loadFromBytes(ByteArray.fromBytes(data)).onComplete(function(bitmap:BitmapData)
                                {
                                    var pixels:Int = bitmap == null ? 0 : bitmap.width * bitmap.height;
                                    if (bitmap == null || decodedPixels + pixels > MAX_DECODED_PIXELS)
                                    {
                                        if (bitmap != null) bitmap.dispose();
                                        failedAtlases++;
                                    }
                                    else
                                    {
                                        decodedPixels += pixels;
                                        var graphic = FlxGraphic.fromBitmapData(bitmap, false, "playground-mod:" + path);
                                        graphics.set(path, graphic);
                                        graphics.set(path.toLowerCase(), graphic);
                                    }
                                    Timer.delay(loadNextAsset, 1);
                                }).onError(function(error:Dynamic)
                                {
                                    failedAtlases++;
                                    trace("[Playground Mods] Could not decode " + path + ": " + error);
                                    Timer.delay(loadNextAsset, 1);
                                });
                            }
                            else
                            {
                                files.set(path, data);
                                files.set(path.toLowerCase(), data);
                                Timer.delay(loadNextAsset, 1);
                            }
                        }
                        catch (error:Dynamic)
                        {
                            failedAtlases++;
                            trace("[Playground Mods] Could not extract " + path + ": " + error);
                            Timer.delay(loadNextAsset, 1);
                        }
                    };
                    loadNextAsset();
                }
                catch (error:Dynamic)
                {
                    callback(false, "Could not extract this ZIP: " + Std.string(error));
                }
            };
            parseJsonChunk();
        }
        catch (error:Dynamic)
        {
            callback(false, "Could not read this ZIP: " + Std.string(error));
        }
    }
}

'''
mod_store.write_text(mod_store_source, encoding="utf-8")

mods_file = root / "source" / "states" / "PlaygroundModsState.hx"
mods_source = r'''package states;

import flixel.text.FlxText.FlxTextAlign;
import openfl.net.FileReference;
import openfl.net.FileFilter;
import openfl.events.Event;
import openfl.events.IOErrorEvent;
import backend.PlaygroundModStore;

class PlaygroundModsState extends MusicBeatState
{
    public static var returnToSandbox:Bool = false;

    private var fileRef:FileReference;
    private var options:Array<FlxText> = [];
    private var selected:Int = 0;
    private var statusText:FlxText;
    private var busy:Bool = false;

    override function create():Void
    {
        super.create();
        FlxG.mouse.visible = true;

        var bg:FlxSprite = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF171326);
        add(bg);

        var top:FlxSprite = new FlxSprite(0, 0).makeGraphic(FlxG.width, 100, FlxColor.BLACK);
        top.alpha = 0.72;
        add(top);

        var title:FlxText = new FlxText(44, 24, FlxG.width - 88, "PLAYGROUND  /  MOD MANAGER", 40);
        title.setFormat(Paths.font("vcr.ttf"), 40, FlxColor.WHITE, FlxTextAlign.LEFT);
        add(title);

        var subtitle:FlxText = new FlxText(48, 78, FlxG.width - 96, "IMPORT A PSYCH ENGINE MOD ZIP", 16);
        subtitle.setFormat(Paths.font("vcr.ttf"), 16, FlxColor.CYAN, FlxTextAlign.LEFT);
        add(subtitle);

        var labels:Array<String> = ["IMPORT MOD ZIP", "REMOVE IMPORTED MOD", "BACK"];
        for (i in 0...labels.length)
        {
            var item:FlxText = new FlxText(90, 210 + i * 86, FlxG.width - 180, labels[i], 30);
            item.setFormat(Paths.font("vcr.ttf"), 30, FlxColor.WHITE, FlxTextAlign.LEFT);
            options.push(item);
            add(item);
        }

        var detail:FlxText = new FlxText(90, 485, FlxG.width - 180,
            "IMPORT EXTRACTS CHARACTERS AND THEIR PNG ATLASES.\nPLAYGROUND RELOADS AFTER IMPORT TO REGISTER THEM.", 18);
        detail.setFormat(Paths.font("vcr.ttf"), 18, FlxColor.WHITE, FlxTextAlign.LEFT);
        add(detail);

        statusText = new FlxText(90, FlxG.height - 95, FlxG.width - 180, "ARROWS: SELECT     ENTER: CONFIRM     ESC: BACK", 16);
        statusText.setFormat(Paths.font("vcr.ttf"), 16, FlxColor.YELLOW, FlxTextAlign.LEFT);
        add(statusText);

        refreshSelection();
    }

    private function refreshSelection():Void
    {
        var labels:Array<String> = ["IMPORT MOD ZIP", "REMOVE IMPORTED MOD", "BACK"];
        for (i in 0...options.length)
        {
            options[i].color = i == selected ? FlxColor.CYAN : FlxColor.WHITE;
            options[i].text = (i == selected ? ">  " : "   ") + labels[i];
        }
    }

    private function browseZip():Void
    {
        if (busy) return;
        fileRef = new FileReference();
        fileRef.addEventListener(Event.SELECT, onZipSelected);
        fileRef.addEventListener(IOErrorEvent.IO_ERROR, onZipError);
        fileRef.browse([new FileFilter("Psych Engine Mod ZIP", "*.zip")]);
    }

    private function onZipSelected(event:Event):Void
    {
        fileRef.removeEventListener(Event.SELECT, onZipSelected);
        if (fileRef.size > 52428800)
        {
            statusText.text = "IMPORT FAILED: ZIP files must be 50 MB or smaller.";
            return;
        }
        fileRef.addEventListener(Event.COMPLETE, onZipLoaded);
        statusText.text = "READING " + fileRef.name + "...";
        busy = true;
        fileRef.load();
    }

    private function onZipLoaded(event:Event):Void
    {
        statusText.text = "EXTRACTING CHARACTER JSON AND PNG ATLASES...";
        PlaygroundModStore.importZip(cast fileRef.data, fileRef.name, function(success:Bool, message:String)
        {
            busy = false;
            if (success)
            {
                statusText.text = message + "  /  RELOADING PLAYGROUND...";
                #if js
                js.Browser.window.location.reload();
                #end
            }
            else
            {
                statusText.text = "IMPORT FAILED: " + message;
                FlxG.sound.play(Paths.sound("cancelMenu"));
            }
        });
    }

    private function onZipError(event:IOErrorEvent):Void
    {
        busy = false;
        statusText.text = "ZIP READ FAILED: " + event.text;
    }

    private function confirmSelection():Void
    {
        if (busy) return;
        switch (selected)
        {
            case 0: browseZip();
            case 1:
                busy = true;
                PlaygroundModStore.clearStored(function(success:Bool, message:String)
                {
                    busy = false;
                    statusText.text = message;
                    if (success)
                    {
                        #if js
                        js.Browser.window.location.reload();
                        #end
                    }
                });
            case 2: goBack();
        }
    }

    private function goBack():Void
    {
        if (returnToSandbox)
        {
            returnToSandbox = false;
            MusicBeatState.switchState(new PlaygroundSandboxState());
        }
        else
        {
            MusicBeatState.switchState(new PlaygroundMenuState());
        }
    }

    override function update(elapsed:Float):Void
    {
        super.update(elapsed);
        if (busy) return;

        if (controls.BACK || FlxG.keys.justPressed.ESCAPE)
        {
            goBack();
            return;
        }

        if (controls.UI_UP_P) selected = (selected + options.length - 1) % options.length;
        if (controls.UI_DOWN_P) selected = (selected + 1) % options.length;

        for (i in 0...options.length)
        {
            if (FlxG.mouse.overlaps(options[i]))
            {
                selected = i;
                if (FlxG.mouse.justPressed) confirmSelection();
            }
        }

        refreshSelection();
        if (controls.ACCEPT) confirmSelection();
    }
}
'''

mods_file.write_text(mods_source, encoding="utf-8")

# Paths.loadAnimateAtlas accepts asset paths. The HTML5 target has no sys.io.File.
# Resolve imported characters from the browser ZIP store in Character's constructor.
character = root / "source" / "objects" / "Character.hx"
character_source = character.read_text(encoding="utf-8")
if "import backend.PlaygroundModStore;" not in character_source:
    if "import backend.Song;" not in character_source:
        raise SystemExit("Could not find Character.hx backend.Song import")
    character_source = character_source.replace(
        "import backend.Song;",
        "import backend.Song;\nimport backend.PlaygroundModStore;",
        1
    )
character_source = character_source.replace(
    "if (!Assets.exists(path))",
    "if (!Assets.exists(path) && PlaygroundModStore.getText(characterPath) == null)",
    1
)
character_source = character_source.replace(
    "loadCharacterFile(Json.parse(Assets.getText(path)));",
    "loadCharacterFile(Json.parse(PlaygroundModStore.getText(characterPath) != null ? PlaygroundModStore.getText(characterPath) : Assets.getText(path)));",
    1
)
if "PlaygroundModStore.getText(characterPath)" not in character_source:
    raise SystemExit("Could not patch Character browser JSON loader")
character.write_text(character_source, encoding="utf-8")

path_source = paths.read_text(encoding="utf-8")

# Resolve the imported ZIP's preloaded character atlas graphics before embedded assets.
image_anchor = "\t\tvar bitmap:BitmapData = null;"
image_code = """\t\t#if html5
\t\tvar importedGraphic = PlaygroundModStore.getGraphic(key);
\t\tif (importedGraphic != null)
\t\t{
\t\t\tlocalTrackedAssets.push("playground-mod:" + key);
\t\t\treturn importedGraphic;
\t\t}
\t\t#end
"""
if image_anchor not in path_source:
    raise SystemExit("Could not locate Paths.image bitmap initialization")
if image_code not in path_source:
    path_source = path_source.replace(image_anchor, image_code + image_anchor, 1)

atlas_specs = [
    ("static public function getAtlas", "xml", "modXml", "FlxAtlasFrames.fromSparrow(imageLoaded, modXml)"),
    ("inline static public function getSparrowAtlas", "xml", "modXml", "FlxAtlasFrames.fromSparrow(imageLoaded, modXml)"),
    ("inline static public function getPackerAtlas", "txt", "modText", "FlxAtlasFrames.fromSpriteSheetPacker(imageLoaded, modText)"),
    ("inline static public function getAsepriteAtlas", "json", "modJson", "FlxAtlasFrames.fromTexturePackerJson(imageLoaded, modJson)"),
]
for signature, extension, variable, return_expression in atlas_specs:
    method_start = path_source.find(signature)
    if method_start < 0:
        raise SystemExit("Could not find " + signature)
    image_line = "\t\tvar imageLoaded:FlxGraphic = image(key, library, allowGPU);"
    line_at = path_source.find(image_line, method_start)
    if line_at < 0:
        raise SystemExit("Could not find image initialization in " + signature)
    insert_at = line_at + len(image_line)
    code = (
        "\n\t\t#if html5\n"
        + "\t\tvar " + variable + ":String = PlaygroundModStore.getText(\"images/\" + key + \"." + extension + "\");\n"
        + "\t\tif (" + variable + " != null) return " + return_expression + ";\n"
        + "\t\t#end"
    )
    if code not in path_source[insert_at:insert_at + 500]:
        path_source = path_source[:insert_at] + code + path_source[insert_at:]

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
