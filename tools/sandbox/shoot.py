#!/usr/bin/env python3
"""Takes the screenshots and records the video for the website, in Russian or English.

usage: shoot.py <ru|en> [shots] [video]
Screenshots land in src/shots/<lang>/ as PNG (1920x1200, the interface at 150 %), the video in
tools/sandbox/work/video-<lang>.mkv; build.py turns them into the files the site serves.
Coordinates are in screen pixels for a 1280x800 window drawn at 150 %.
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ctl import send  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MASCOT = os.path.join(REPO, "src", "assets", "img", "mascot.png")
TMP = "/tmp/claude-1000/shoot"

# main window
TILE = {"vanilla": (666, 240), "hardcore": (844, 240), "beta": (1020, 240), "atm10": (490, 460),
        "create": (666, 460), "cobblemon": (844, 460), "quilt": (1020, 460)}
THEMES_BUTTON = (74, 404)
THEME = {"sakura": (130, 594), "prixum": (132, 550), "midnight": (140, 504), "light": (122, 460)}
SETTINGS_BUTTON = (120, 350)
ACCOUNT_BUTTON = (178, 1110)
SKINS_ITEM = (112, 1000)
LAUNCH_BUTTON = (1580, 736)
# skins dialog and settings: longer English labels move some of them
BY_LANG = {
    "ru": {"preview": (320, 440), "notch": (1434, 480), "mascot": (680, 820), "skins_cancel": (1784, 1032),
           "settings_ok": (1580, 1062), "settings_cancel": (1686, 1062)},
    "en": {"preview": (394, 440), "notch": (836, 820), "mascot": (1340, 820), "skins_cancel": (1724, 1032),
           "settings_ok": (1592, 1062), "settings_cancel": (1692, 1062)},
}
APPEARANCE_PAGE = (256, 244)
SETTINGS_SCROLL = ((1732, 200), (1732, 470))
WALLPAPER_SWITCH = (530, 552)
SETTINGS_SEARCH = (280, 40)


def start(app, lang, **env):
    full = dict(os.environ, MASCOT=MASCOT, **env)
    for key in ("THEME", "WALLPAPER"):
        if key not in env:
            full.pop(key, None)
    subprocess.run([os.path.join(HERE, "start.sh"), app, lang], env=full, check=True, stdout=subprocess.DEVNULL)
    time.sleep(1.5)


def do(cmd, **args):
    reply = send(cmd, **args)
    if not reply.get("ok"):
        raise RuntimeError(f"{cmd} {args}: {reply}")
    return reply


def click(point, ms=0):
    do("click", x=point[0], y=point[1], ms=ms)


def glide(point, ms):
    do("glide", x=point[0], y=point[1], ms=ms)


def wait(ms):
    time.sleep(ms / 1000)


def shot(lang, name):
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"{lang}-{name}.png")
    do("move", x=1919, y=1199)  # keep hover effects out of the picture
    wait(400)
    do("shot", path=path)
    out = os.path.join(REPO, "src", "shots", lang)
    os.makedirs(out, exist_ok=True)
    shutil.copy(path, os.path.join(out, f"{name}.png"))
    print("shot", lang, name, flush=True)


def shots(lang):
    at = BY_LANG[lang]
    start("prixum", lang)
    shot(lang, "main")
    click(SETTINGS_BUTTON)
    wait(900)
    click(APPEARANCE_PAGE)
    wait(700)
    shot(lang, "settings-themes")
    click(SETTINGS_SEARCH)
    wait(300)
    do("type", text="java", delay=0.08)
    wait(900)
    shot(lang, "settings-search")
    click(at["settings_cancel"])
    wait(600)
    click(ACCOUNT_BUTTON)
    wait(500)
    click(SKINS_ITEM)
    wait(1800)
    shot(lang, "skins")

    start("prixum", lang, WALLPAPER="on")
    shot(lang, "glass")

    for theme in ("nova-sakura", "nova-light", "nova-midnight"):
        start("prixum", lang, THEME=theme)
        shot(lang, theme)

    start("prism", lang)
    wait(2500)
    shot(lang, "prism")


def video(lang):
    at = BY_LANG[lang]
    start("prixum", lang, WALLPAPER="ready")
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"video-{lang}.mkv")
    do("move", x=980, y=640)
    do("record", path=path, fps=30)
    wait(400)
    # hovering the instances and picking one
    glide(TILE["vanilla"], 600)
    wait(150)
    glide(TILE["hardcore"], 400)
    glide(TILE["cobblemon"], 500)
    click(TILE["cobblemon"])
    wait(700)
    # three themes in a row
    for theme, pause in (("sakura", 900), ("midnight", 900), ("prixum", 600)):
        click(THEMES_BUTTON, 550)
        wait(250)
        click(THEME[theme], 400)
        wait(pause)
    # skins walking in the grid, turning the preview, trying another skin
    click(ACCOUNT_BUTTON, 700)
    wait(300)
    click(SKINS_ITEM, 350)
    wait(1200)
    do("drag", x0=at["preview"][0], y0=at["preview"][1], x1=at["preview"][0] + 150, y1=at["preview"][1], ms=650, approach=450)
    do("drag", x0=at["preview"][0] + 150, y0=at["preview"][1], x1=at["preview"][0] - 110, y1=at["preview"][1], ms=750, approach=120)
    wait(200)
    click(at["notch"], 600)
    wait(1000)
    click(at["mascot"], 550)
    wait(800)
    click(at["skins_cancel"], 600)
    wait(350)
    # the wallpaper turns the tiles into frosted glass
    click(SETTINGS_BUTTON, 600)
    wait(700)
    click(APPEARANCE_PAGE, 450)
    wait(450)
    do("drag", x0=SETTINGS_SCROLL[0][0], y0=SETTINGS_SCROLL[0][1], x1=SETTINGS_SCROLL[1][0], y1=SETTINGS_SCROLL[1][1],
       ms=450, approach=450)
    wait(350)
    click(WALLPAPER_SWITCH, 550)
    wait(1100)
    click(at["settings_ok"], 600)
    wait(1100)
    glide(TILE["hardcore"], 550)
    wait(300)
    glide(TILE["beta"], 450)
    wait(400)
    # the settings search finds things on every page
    click(SETTINGS_BUTTON, 600)
    wait(900)
    glide(SETTINGS_SEARCH, 450)
    do("chord", keysyms=[0xffe3, 0x66])  # Ctrl+F puts the cursor into the search
    wait(200)
    do("type", text="java", delay=0.12)
    wait(1400)
    click(at["settings_cancel"], 600)
    wait(500)
    glide(LAUNCH_BUTTON, 600)
    wait(900)
    frames = do("stop")["frames"]
    shutil.copy(path, os.path.join(HERE, "work", f"video-{lang}.mkv"))
    print("video", lang, frames / 30, "s", flush=True)


if __name__ == "__main__":
    lang = sys.argv[1]
    what = sys.argv[2:] or ["shots", "video"]
    if "shots" in what:
        shots(lang)
    if "video" in what:
        video(lang)
    send("quit")
