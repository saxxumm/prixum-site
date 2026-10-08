#!/usr/bin/env python3
"""Creates a data directory with made up instances for screenshots and recordings of Prixum or Prism Launcher.

usage: make_demo.py <dir> <prixum|prism> <ru|en>
env:   THEME            application theme (default nova-prixum for Prixum, dark for Prism)
       WALLPAPER        "on" shows the demo wallpaper, "ready" sets it up but leaves it off
       MASCOT           path of the mascot skin, worn by the demo account
"""
import base64
import json
import struct
import os
import shutil
import sys
import time
from datetime import datetime, timezone

root, app, lang = sys.argv[1], sys.argv[2], sys.argv[3]
CONTENT = os.path.expanduser("~/PrismLauncher/build/demo-content")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_NAME = "PrixumLauncher" if app == "prixum" else "PrismLauncher"
# where the directory shows up inside the sandbox
SANDBOX_ROOT = f"/home/steve/.local/share/{DATA_NAME}"

shutil.rmtree(root, ignore_errors=True)
os.makedirs(os.path.join(root, "instances"))
now = int(time.time())
H = 3600

T = {
    "ru": {"hardcore": "Хардкор", "friends": "Друзья SMP", "modpacks": "Модпаки", "servers": "Сервера"},
    "en": {"hardcore": "Hardcore", "friends": "Friends SMP", "modpacks": "Modpacks", "servers": "Servers"},
}[lang]

LOADERS = {
    "fabric": ("net.fabricmc.fabric-loader", "Fabric Loader"),
    "forge": ("net.minecraftforge", "Forge"),
    "neoforge": ("net.neoforged", "NeoForge"),
    "quilt": ("org.quiltmc.quilt-loader", "Quilt Loader"),
}
instances = [
    # folder, name, icon, minecraft, loader, loader version, total played, last played ago, group
    ("fabric-perf", "Fabric Performance", "fabricmc", "1.21.4", "fabric", "0.16.9", 61 * H + 1260, 2 * H, None),
    ("vanilla", "Vanilla 1.21.4", "grass", "1.21.4", None, None, 14 * H + 300, 26 * H, None),
    ("hardcore", T["hardcore"], "skeleton", "1.21.4", None, None, 9 * H + 2400, 5 * 24 * H, None),
    ("beta", "Beta 1.7.3", "steve", "b1.7.3", None, None, 3 * H + 900, 40 * 24 * H, None),
    ("create", "Create: Above and Beyond", "gear", "1.18.2", "forge", "40.2.0", 120 * H + 600, 3 * 24 * H, T["modpacks"]),
    ("atm10", "All the Mods 10", "netherstar", "1.21.1", "neoforge", "21.1.77", 88 * H, 24 * H, T["modpacks"]),
    ("cobblemon", "Cobblemon", "fox", "1.21.1", "fabric", "0.16.9", 35 * H, 9 * 24 * H, T["modpacks"]),
    ("quilt", "Quilt Sandbox", "quiltmc", "1.20.1", "quilt", "0.26.4", 2 * H, 20 * 24 * H, T["modpacks"]),
    ("hypixel", "Hypixel 1.8.9", "diamond", "1.8.9", "forge", "11.15.1.2318", 210 * H, 4 * H, T["servers"]),
    ("smp", T["friends"], "creeper", "1.21.4", "fabric", "0.16.9", 47 * H, 6 * H, T["servers"]),
]
groups = {}
for folder, name, icon, mc, loader, lver, played, ago, group in instances:
    d = os.path.join(root, "instances", folder)
    os.makedirs(os.path.join(d, "minecraft"))
    with open(os.path.join(d, "instance.cfg"), "w") as f:
        f.write("[General]\nConfigVersion=1.3\nInstanceType=OneSix\n")
        f.write(f"name={name}\niconKey={icon}\n")
        f.write(f"totalTimePlayed={played}\nlastTimePlayed={min(played, 2 * H + 420)}\nlastLaunchTime={(now - ago) * 1000}\n")
    components = [{"uid": "net.minecraft", "version": mc, "important": True, "cachedName": "Minecraft", "cachedVersion": mc}]
    if loader:
        uid, lname = LOADERS[loader]
        components.append({"uid": uid, "version": lver, "cachedName": lname, "cachedVersion": lver})
    with open(os.path.join(d, "mmc-pack.json"), "w") as f:
        json.dump({"formatVersion": 1, "components": components}, f, indent=1)
    if group:
        groups.setdefault(group, {"hidden": False, "instances": []})["instances"].append(folder)
with open(os.path.join(root, "instances", "instgroups.json"), "w") as f:
    json.dump({"formatVersion": "1", "groups": groups}, f, indent=1)

# real mods, resource packs and shaders for the content pages, one mod disabled to show both states
game = os.path.join(root, "instances", "fabric-perf", "minecraft")
for sub in ("mods", "resourcepacks", "shaderpacks"):
    if os.path.isdir(os.path.join(CONTENT, sub)):
        shutil.copytree(os.path.join(CONTENT, sub), os.path.join(game, sub))
for f in os.listdir(os.path.join(game, "mods")) if os.path.isdir(os.path.join(game, "mods")) else []:
    if f.startswith("entityculling"):
        os.rename(os.path.join(game, "mods", f), os.path.join(game, "mods", f + ".disabled"))

# saved skins, the mascot is the one the account wears
skins = os.path.join(root, "skins")
os.makedirs(os.path.join(skins, "capes"))
WORN_URL = "https://textures.minecraft.net/texture/prixum-mascot-demo"
entries = []
mascot = os.environ.get("MASCOT")
if mascot:
    shutil.copy(mascot, os.path.join(skins, "Prixum.png"))
    entries.append({"name": "Prixum", "capeId": "", "url": WORN_URL, "model": "SLIM"})
for f in sorted(os.listdir(os.path.join(CONTENT, "skins"))):
    if f.startswith("cape-") or f in ("Technoblade.png",):
        continue
    shutil.copy(os.path.join(CONTENT, "skins", f), os.path.join(skins, f))
    entries.append({"name": f[:-4], "capeId": "", "url": "", "model": "SLIM" if f == "Dream.png" else "CLASSIC"})
with open(os.path.join(skins, "index.json"), "w") as f:
    json.dump({"skins": entries}, f, indent=1)
capes = []
for i, (cape_file, alias) in enumerate((("cape-Grumm.png", "Migrator"), ("cape-jeb_.png", "Vanilla"))):
    path = os.path.join(CONTENT, "skins", cape_file)
    if os.path.exists(path):
        cape_id = f"demo-cape-{i + 1}"
        shutil.copy(path, os.path.join(skins, "capes", cape_id + ".png"))
        capes.append({"id": cape_id, "url": "", "alias": alias, "data": base64.b64encode(open(path, "rb").read()).decode()})

far = now + 10 * 365 * 24 * H
token = lambda: {"token": "demo", "refresh_token": "demo", "iat": now, "exp": far, "extra": {}}
account = {
    "type": "MSA", "msa-client-id": "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb",
    "msa": token(), "utoken": token(), "xrp-mc": token(), "ygg": token(),
    "profile": {"id": "8667ba71b85a4004af54457a9734eed7", "name": "Steve",
                "skin": {"id": "", "url": WORN_URL if mascot else "", "variant": "slim" if mascot else "classic"}, "capes": capes},
    "entitlement": {"ownsMinecraft": True, "canPlayMinecraft": True},
    "active": True,
}
with open(os.path.join(root, "accounts.json"), "w") as f:
    json.dump({"formatVersion": 3, "accounts": [account]}, f, indent=1)

# a maximized window: QWidget::saveGeometry() version 3, there is no window manager to maximize it
scale = float(os.environ.get("QT_SCALE_FACTOR", "1.5"))
sw, sh = round(int(os.environ.get("VW", 1920)) / scale), round(int(os.environ.get("VH", 1200)) / scale)
rect = struct.pack(">iiii", 0, 0, sw - 1, sh - 1)
geometry = struct.pack(">IHH", 0x1D9D0CB, 3, 0) + rect + rect + struct.pack(">iBBi", 0, 1, 0, sw) + rect

settings = [f"MainWindowGeometry={base64.b64encode(geometry).decode()}",
    f"Language={lang}", "AutomaticJavaDownload=true", "UserAskedAboutAutomaticJavaDownload=true", "IgnoreJavaWizard=true",
    "MainWindowState=", "SelectedInstance=fabric-perf", "InstSortMode=LastLaunch", "MenuBarInsteadOfToolBar=false",
    "ShowConsole=false", "AutoCloseConsole=false", "ProxyType=Default", "AutoUpdate=false",
]
if app == "prixum":
    settings += [f"ApplicationTheme={os.environ.get('THEME', 'nova-prixum')}", "IconTheme=nova", "NovaDesignIntroduced=true",
                 "NovaNewsVisible=false", "RenderScaleEnabled=true", "RenderScalePercent=50", "RenderScaleFilter=nearest"]
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    settings.append("SkinHistoryState=" + json.dumps(json.dumps({account["profile"]["id"]: {"checked": checked, "seen": []}})))
    wallpaper = os.environ.get("WALLPAPER")
    if wallpaper:
        shutil.copy(os.path.join(CONTENT, "wallpaper.png"), os.path.join(root, "wallpaper.png"))
        settings += [f"InstanceWallpaperEnabled={'true' if wallpaper == 'on' else 'false'}",
                     f"InstanceWallpaper={SANDBOX_ROOT}/wallpaper.png"]
    cfg = "prixumlauncher.cfg"
    for name in ("PrismLauncher", "PolyMC", "MultiMC"):
        open(os.path.join(root, f"{name}_nomigrate.txt"), "w").close()
else:
    settings += [f"ApplicationTheme={os.environ.get('THEME', 'dark')}", "IconTheme=pe_colored"]
    cfg = "prismlauncher.cfg"
with open(os.path.join(root, cfg), "w") as f:
    f.write("[General]\n" + "\n".join(settings) + "\n")

# translations and metadata already downloaded by the real install, so the demo works offline
real = os.path.expanduser(f"~/.local/share/{DATA_NAME}")
for sub in ("translations", "meta"):
    if os.path.isdir(os.path.join(real, sub)):
        shutil.copytree(os.path.join(real, sub), os.path.join(root, sub))
print("demo data in", root)
