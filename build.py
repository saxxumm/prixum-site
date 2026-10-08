#!/usr/bin/env python3
"""Builds prixum.org into docs/ (GitHub Pages): four pages in Russian, English and Ukrainian.

usage: build.py [--refresh]
  --refresh   fetches the release list from GitHub before building (needs the gh command line tool)

Screenshots come from src/shots/<lang>/*.png and the videos from src/assets/video, both made by tools/sandbox.
Release notes are rendered once through the GitHub markdown API and cached in src/releases/cache.
"""
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "docs")
sys.path.insert(0, SRC)
from i18n import FAQ, LANGS, LOCALE, NAME, PREFIX, SHORT, SHOTS, T  # noqa: E402

REPO = "saxxumm/PrixumLauncher"
SITE = "https://prixum.org"
TELEGRAM = "https://t.me/prixum_launcher"
GITHUB = f"https://github.com/{REPO}"
PAGES = {"home": "", "download": "download/", "changelog": "changelog/", "faq": "faq/"}
FILES = {
    "win-x64-setup": "PrixumLauncher-Windows-MSVC-Setup-{v}.exe",
    "win-x64-portable": "PrixumLauncher-Windows-MSVC-Portable-{v}.zip",
    "win-arm-setup": "PrixumLauncher-Windows-MSVC-arm64-Setup-{v}.exe",
    "win-arm-portable": "PrixumLauncher-Windows-MSVC-arm64-Portable-{v}.zip",
    "mac-dmg": "PrixumLauncher-macOS-{v}.dmg",
    "mac-portable": "PrixumLauncher-macOS-Portable-{v}.zip",
    "linux-x64-appimage": "PrixumLauncher-Linux-x86_64.AppImage",
    "linux-x64-portable": "PrixumLauncher-Linux-Qt6-Portable-{v}.tar.gz",
    "linux-arm-appimage": "PrixumLauncher-Linux-aarch64.AppImage",
    "linux-arm-portable": "PrixumLauncher-Linux-aarch64-Qt6-Portable-{v}.tar.gz",
    "arch-pkg": "prixumlauncher-{v}-1-x86_64.pkg.tar.zst",
}
MONTHS = {
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    "uk": ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
UNITS = {"ru": "МБ", "en": "MB", "uk": "МБ"}

ICONS = {
    "download": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11 3h2v10.2l3.6-3.6 1.4 1.4-6 6-6-6 1.4-1.4 3.6 3.6zM4 18h16v2H4z"/></svg>',
    "telegram": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21.4 4.3 2.9 11.4c-1.3.5-1.2 1.3-.2 1.6l4.7 1.5 1.8 5.6c.2.6.5.8 1 .8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.6c.3-1.3-.5-1.9-1.6-1.5zM9.6 14.3l-.4 4-1.4-4.4L18 7.6z"/></svg>',
    "github": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.4-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.2-.4-1.3.1-2.7 0 0 .8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.5.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8V21c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/></svg>',
    "sun": '<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0-5 1 3h-2zm0 20-1-3h2zM2 12l3-1v2zm20 0-3 1v-2zM4.9 4.9l2.8 1.4-1.4 1.4zm14.2 14.2-2.8-1.4 1.4-1.4zM4.9 19.1l1.4-2.8 1.4 1.4zM19.1 4.9l-1.4 2.8-1.4-1.4z"/></svg>'
           '<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5 9 9 0 1 0 20.5 14.6z"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm-1.5 2.2A8 8 0 0 0 4.1 11h3.4c.1-2.5.9-4.9 3-6.8zm3 0c2.1 1.9 2.9 4.3 3 6.8h3.4a8 8 0 0 0-6.4-6.8zM9.5 11h5c-.1-2.3-.9-4.4-2.5-6-1.6 1.6-2.4 3.7-2.5 6zm-5.4 2a8 8 0 0 0 6.4 6.8c-2.1-1.9-2.9-4.3-3-6.8zm5.4 0c.1 2.3.9 4.4 2.5 6 1.6-1.6 2.4-3.7 2.5-6zm7 0c-.1 2.5-.9 4.9-3 6.8a8 8 0 0 0 6.4-6.8z"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/></svg>',
    "spark": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2l2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z"/></svg>',
    "check": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 11-11-1.4-1.4z"/></svg>',
    "arrows": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 6 3 12l6 6v-4h6v4l6-6-6-6v4H9z"/></svg>',
    "scale": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 3h8v2H6.4l4.3 4.3-1.4 1.4L5 6.4V11H3zm18 18h-8v-2h4.6l-4.3-4.3 1.4-1.4 4.3 4.3V13h2z"/></svg>',
    "box": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2 3 7v10l9 5 9-5V7zm0 2.3L18.6 8 12 11.7 5.4 8zM5 9.7l6 3.3v6.6l-6-3.3zm8 9.9V13l6-3.3v6.6z"/></svg>',
    "puzzle": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M10 3a2 2 0 0 1 2 2v1h4a1 1 0 0 1 1 1v4h1a2 2 0 1 1 0 4h-1v4a1 1 0 0 1-1 1h-4v-1a2 2 0 1 0-4 0v1H4a1 1 0 0 1-1-1v-4h1a2 2 0 1 0 0-4H3V7a1 1 0 0 1 1-1h4V5a2 2 0 0 1 2-2z"/></svg>',
    "users": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8zm7.5 1a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM9 14c4 0 7 2 7 4.5V20H2v-1.5C2 16 5 14 9 14zm9 0c2.8.2 4 1.8 4 3.5V20h-4z"/></svg>',
    "move": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 4h7l2 2h7v13H4zm9 5v3H8v2h5v3l4-4z"/></svg>',
    "code": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="m8.6 16.6-4.6-4.6 4.6-4.6L7.2 6 1.2 12l6 6zm6.8 0 4.6-4.6-4.6-4.6L16.8 6l6 6-6 6z"/></svg>',
    "windows": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 5.5 10.4 4.5v7H3zm8.4-1.1L21 3v8.5h-9.6zM3 12.5h7.4v7L3 18.5zm8.4 0H21V21l-9.6-1.4z"/></svg>',
    "apple": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.4 12.6c0-2.6 2.1-3.8 2.2-3.9-1.2-1.8-3.1-2-3.7-2-1.6-.2-3.1.9-3.9.9-.8 0-2-.9-3.4-.9-1.7 0-3.3 1-4.2 2.6-1.8 3.1-.5 7.7 1.3 10.2.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8s2 .8 3.4.8c1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9 0 0-2.7-1-2.7-4.1zM13.9 5c.7-.8 1.2-2 1-3.2-1 .1-2.2.7-2.9 1.5-.6.7-1.2 1.9-1 3 1.1.1 2.2-.5 2.9-1.3z"/></svg>',
    "linux": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2c2.2 0 3.6 1.8 3.6 4.4 0 1.2.4 2.2 1.2 3.4 1.2 1.7 2.4 3.6 2.4 6 0 .6-.1 1.1-.3 1.6.8.4 1.3 1 1.3 1.7 0 1.4-1.9 2.9-4 2.9-1.2 0-2.1-.5-2.7-1.1-.5.1-1 .1-1.5.1s-1 0-1.5-.1c-.6.6-1.5 1.1-2.7 1.1-2.1 0-4-1.5-4-2.9 0-.7.5-1.3 1.3-1.7-.2-.5-.3-1-.3-1.6 0-2.4 1.2-4.3 2.4-6 .8-1.2 1.2-2.2 1.2-3.4C8.4 3.8 9.8 2 12 2zm-1.6 4.2a.8.8 0 1 0 0 1.6.8.8 0 0 0 0-1.6zm3.2 0a.8.8 0 1 0 0 1.6.8.8 0 0 0 0-1.6zM12 9c-.9 0-1.8.5-1.8 1s.9 1 1.8 1 1.8-.5 1.8-1-.9-1-1.8-1z"/></svg>',
    "arch": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2c-.9 2.2-1.5 3.7-2.4 5.6.6.6 1.3 1.3 2.4 2-1.2-.5-2-1-2.6-1.6C8.2 10.5 6.4 14 3 20c2.6-1.5 4.6-2.4 6.4-2.8-.1-.3-.1-.7-.1-1 0-2.6 1.2-4.6 2.7-4.5 1.5.1 2.6 2.4 2.6 5v.6c1.8.4 3.8 1.3 6.4 2.7-.5-1-1-1.8-1.4-2.6-.7-.6-1.5-1.3-3-2.1 1 .3 1.8.6 2.4 1C17 12.4 15.4 9 12 2z"/></svg>',
}


def esc(text):
    return html.escape(text, quote=True)


def fmt_date(iso, lang):
    year, month, day = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    if lang == "en":
        return f"{MONTHS['en'][month - 1]} {day}, {year}"
    return f"{day} {MONTHS[lang][month - 1]} {year}"


def url(lang, page):
    return PREFIX[lang] + PAGES[page]


def digest(path):
    return hashlib.sha1(open(path, "rb").read()).hexdigest()[:10]


# ---------------------------------------------------------------- assets

def build_assets():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for sub in ("css", "js", "img"):
        shutil.copytree(os.path.join(SRC, "assets", sub), os.path.join(OUT, "assets", sub))
    # one script for every page: the skin renderer first, the site after it
    js = open(os.path.join(SRC, "assets", "js", "skinview.js")).read() + "\n" + open(os.path.join(SRC, "assets", "js", "site.js")).read()
    with open(os.path.join(OUT, "assets", "js", "app.js"), "w") as f:
        f.write(js)
    shutil.copy(os.path.join(SRC, "assets", "img", "logo.svg"), os.path.join(OUT, "favicon.svg"))

    shots = os.path.join(OUT, "assets", "shots")
    for lang in sorted(set(SHOTS.values())):
        folder = os.path.join(SRC, "shots", lang)
        os.makedirs(os.path.join(shots, lang))
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".png"):
                continue
            image = Image.open(os.path.join(folder, name)).convert("RGB")
            for width in (1600, 960):
                scaled = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
                scaled.save(os.path.join(shots, lang, f"{name[:-4]}-{width}.webp"), "WEBP", quality=84, method=6)

    video = os.path.join(OUT, "assets", "video")
    os.makedirs(video)
    for lang in sorted(set(SHOTS.values())):
        path = os.path.join(SRC, "assets", "video", f"prixum-{lang}.mp4")
        if os.path.exists(path):
            shutil.copy(path, video)
        poster = os.path.join(SRC, "assets", "video", f"prixum-{lang}-poster.png")
        if os.path.exists(poster):
            Image.open(poster).convert("RGB").save(os.path.join(video, f"prixum-{lang}-poster.webp"), "WEBP", quality=82, method=6)

    with open(os.path.join(OUT, "CNAME"), "w") as f:
        f.write("prixum.org\n")
    open(os.path.join(OUT, ".nojekyll"), "w").close()


# ---------------------------------------------------------------- releases

def gh(*args, data=None):
    return subprocess.run(["gh", *args], input=data, capture_output=True, text=True, check=True).stdout


def markdown(text):
    cache = os.path.join(SRC, "releases", "cache")
    os.makedirs(cache, exist_ok=True)
    key = hashlib.sha1(text.encode()).hexdigest()
    path = os.path.join(cache, key + ".html")
    if not os.path.exists(path):
        rendered = gh("api", "markdown", "-f", f"text={text}", "-f", "mode=gfm", "-f", f"context={REPO}")
        rendered = rendered.replace(' dir="auto"', "").replace(' class="notranslate"', "").replace(' rel="nofollow"', "")
        with open(path, "w") as f:
            f.write(rendered)
    return open(path).read()


SECTION = re.compile(r"<details>\s*<summary>\s*(English|Українська)\s*</summary>(.*?)</details>", re.S | re.I)
DOWNLOAD_HEADING = re.compile(r"^## (Какой файл скачать|Which file to download|Який файл завантажити).*", re.S | re.M)


def notes_for(release, lang):
    body = (release.get("body") or "").replace("\r\n", "\n")
    sections = {("en" if m.group(1).lower() == "english" else "uk"): m.group(2) for m in SECTION.finditer(body)}
    if lang == "ru":
        text = SECTION.sub("", body)
    else:
        local = os.path.join(SRC, "releases", f"{release['tag_name']}.{lang}.md")
        text = sections.get(lang) or (open(local).read() if os.path.exists(local) else SECTION.sub("", body))
    return DOWNLOAD_HEADING.sub("", text).strip()


def load_releases(refresh):
    path = os.path.join(SRC, "releases", "releases.json")
    if refresh:
        with open(path, "w") as f:
            f.write(gh("api", f"repos/{REPO}/releases", "--paginate"))
    releases = [r for r in json.load(open(path)) if not r.get("draft")]
    for r in releases:
        r["notes"] = {lang: markdown(notes_for(r, lang)) for lang in LANGS}
    return releases


# ---------------------------------------------------------------- page parts

def strings_for_js(lang):
    keys = ["theme_dark", "theme_light", "tryon_reset", "tryon_loading", "tryon_done", "tryon_bad_name", "tryon_failed",
            "cta_download", "cta_download_for", "release_line", "mobile_note", "os_windows", "os_macos", "os_linux"]
    strings = {k: T[lang][k] for k in keys}
    strings["mb"] = UNITS[lang]
    return strings


def head(lang, page, title, description, latest):
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE}{url(l, page)}">' for l in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{url("ru", page)}">'
    css = f"/assets/css/site.css?v={digest(os.path.join(OUT, 'assets', 'css', 'site.css'))}"
    # the browser language picks the page on the first visit to the Russian root, a choice made later is remembered
    redirect = ""
    if lang == "ru":
        paths = json.dumps({l: url(l, page) for l in LANGS})
        redirect = (
            "try{if(!localStorage.getItem('lang')){var p=" + paths + ";"
            "var l=(navigator.languages||[navigator.language||'ru']).map(function(x){return (x||'').slice(0,2).toLowerCase()});"
            "var w=l.indexOf('ru')>=0&&(l.indexOf('uk')<0||l.indexOf('ru')<l.indexOf('uk'))?'ru':l.indexOf('uk')>=0?'uk':l[0]==='be'||l[0]==='kk'?'ru':'en';"
            "localStorage.setItem('lang',w);if(w!=='ru')location.replace(p[w]+location.hash)}}catch(e){}"
        )
    return f"""<!doctype html>
<html lang="{lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{SITE}{url(lang, page)}">
{alternates}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Prixum Launcher">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{SITE}{url(lang, page)}">
<meta property="og:image" content="{SITE}/assets/img/og.png">
<meta property="og:locale" content="{LOCALE[lang].replace('-', '_')}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b0910">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script>try{{var t=localStorage.getItem('theme');if(t==='light')document.documentElement.dataset.theme='light'}}catch(e){{}}{redirect}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=Unbounded:wght@600;700&display=swap">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main">{esc(T[lang]['skip'])}</a>
<div class="ambient" aria-hidden="true"></div>
<canvas id="petals" aria-hidden="true"></canvas>
"""


def nav(lang, page):
    t = T[lang]
    logo = open(os.path.join(SRC, "assets", "img", "logo.svg")).read()
    logo = logo[logo.index("<svg"):].replace("<svg ", '<svg aria-hidden="true" focusable="false" ', 1)
    logo = re.sub(r"<title>.*?</title>", "", logo, flags=re.S)
    links = "".join(
        f'<a href="{url(lang, p)}"{" aria-current=\"page\"" if p == page else ""}>{esc(t["nav_" + p])}</a>'
        for p in ("home", "download", "changelog", "faq")
    )
    langs = "".join(
        f'<a href="{url(l, page)}" hreflang="{l}" lang="{l}" data-lang-link="{l}"{" aria-current=\"true\"" if l == lang else ""}>'
        f'{NAME[l]}<span>{SHORT[l]}</span></a>'
        for l in LANGS
    )
    return f"""<div class="nav-wrap">
<nav class="nav" aria-label="Prixum">
  <a class="brand" href="{url(lang, 'home')}">{logo}<span>Prixum</span></a>
  <div class="nav-links" id="nav-links">{links}</div>
  <div class="nav-tools">
    <details class="lang">
      <summary aria-label="{esc(t['nav_language'])}">{ICONS['globe']}{SHORT[lang]}</summary>
      <div class="lang-menu">{langs}</div>
    </details>
    <button class="icon-btn theme-btn" type="button" aria-label="{esc(t['theme_light'])}">{ICONS['sun']}</button>
    <a class="icon-btn" href="{TELEGRAM}" aria-label="{esc(t['telegram'])}" title="{esc(t['telegram'])}">{ICONS['telegram']}</a>
    <a class="icon-btn gh" href="{GITHUB}" aria-label="{esc(t['github'])}" title="{esc(t['github'])}">{ICONS['github']}</a>
    <button class="icon-btn menu-btn" type="button" aria-label="{esc(t['nav_menu'])}" aria-expanded="false" aria-controls="nav-links">{ICONS['menu']}</button>
  </div>
</nav>
</div>
"""


def footer(lang, page, data):
    t = T[lang]
    langs = "".join(f'<li><a href="{url(l, page)}" hreflang="{l}" lang="{l}" data-lang-link="{l}">{NAME[l]}</a></li>' for l in LANGS)
    return f"""<footer class="footer">
<div class="wrap">
  <div class="footer-grid">
    <div class="footer-about">
      <a class="brand" href="{url(lang, 'home')}">Prixum Launcher</a>
      <p>{esc(t['footer_about'])}</p>
    </div>
    <div><h2>{esc(t['footer_launcher'])}</h2><ul>
      <li><a href="{url(lang, 'download')}">{esc(t['nav_download'])}</a></li>
      <li><a href="{url(lang, 'changelog')}">{esc(t['nav_changelog'])}</a></li>
      <li><a href="{url(lang, 'faq')}">{esc(t['nav_faq'])}</a></li>
    </ul></div>
    <div><h2>{esc(t['footer_community'])}</h2><ul>
      <li><a href="{TELEGRAM}">Telegram</a></li>
      <li><a href="{GITHUB}">GitHub</a></li>
      <li><a href="{GITHUB}/issues">{esc(t['report_bug'])}</a></li>
    </ul></div>
    <div><h2>{esc(t['nav_language'])}</h2><ul>{langs}</ul></div>
  </div>
  <p class="legal">{esc(t['footer_legal'])}</p>
</div>
</footer>
<script id="site-data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
<script src="/assets/js/app.js?v={digest(os.path.join(OUT, 'assets', 'js', 'app.js'))}" defer></script>
</body>
</html>
"""


def picture(shot_lang, name, alt, sizes="(max-width: 960px) 100vw, 60vw", eager=False):
    base = f"/assets/shots/{shot_lang}/{name}"
    path = os.path.join(SRC, "shots", shot_lang, name + ".png")
    width, height = Image.open(path).size
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img src="{base}-1600.webp" srcset="{base}-960.webp 960w, {base}-1600.webp 1600w" sizes="{sizes}" '
            f'width="{width}" height="{height}" alt="{esc(alt)}" {loading}>')


def download_button(lang, extra=""):
    t = T[lang]
    return (f'<a class="btn btn-primary{extra}" href="{url(lang, "download")}" data-download-main data-fallback="{url(lang, "download")}">'
            f'{ICONS["download"]}<span>{esc(t["cta_download"])}</span></a>')


# ---------------------------------------------------------------- pages

def page_data(lang, release, releases):
    return {
        "lang": lang, "locale": LOCALE[lang], "repo": REPO, "strings": strings_for_js(lang),
        "release": {"version": release["tag_name"], "date": release["published_at"], "files": FILES,
                    "sizes": {a["name"]: a["size"] for a in release.get("assets", [])}},
        "known_releases": [r["tag_name"] for r in releases],
    }


def home(lang, release, releases):
    t = T[lang]
    shots = SHOTS[lang]
    version = release["tag_name"]
    more = [
        ("scale", "m_scaling"), ("box", "m_newinstance"), ("puzzle", "m_mods"),
        ("users", "m_accounts"), ("move", "m_migrate"), ("code", "m_open"),
    ]
    more_items = "".join(
        f'<li><span class="ico">{ICONS[icon]}</span><strong>{esc(t[key + "_title"])}</strong><span>{esc(t[key + "_text"])}</span></li>'
        for icon, key in more
    )

    def feature(key, media, flip=False):
        return f"""<article class="feature{' flip' if flip else ''}">
  <div class="feature-copy">
    <h3>{esc(t[key + '_title'])}</h3>
    <p>{esc(t[key + '_text'])}</p>
    <p class="more">{ICONS['check']}<span>{esc(t[key + '_more'])}</span></p>
  </div>
  <div class="feature-media">{media}</div>
</article>"""

    stack = (f'<div class="stack" role="img" aria-label="{esc(t["f_themes_alt"])}">'
             + "".join(picture(shots, n, "", "(max-width: 960px) 76vw, 45vw").replace(' alt=""', ' alt="" aria-hidden="true"')
                       for n in ("nova-sakura", "nova-light", "nova-midnight"))
             + "</div>")
    body = f"""<main id="main">
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <a class="badge" href="{url(lang, 'changelog')}"><i>{ICONS['spark']}</i><span>{esc(t['hero_badge'].format(version=version))}</span></a>
      <h1>{esc(t['hero_title'])}</h1>
      <p class="lead">{esc(t['hero_lead'])}</p>
      <div class="cta-row">
        {download_button(lang)}
        <a class="btn btn-glass" href="{TELEGRAM}">{ICONS['telegram']}<span>{esc(t['cta_telegram'])}</span></a>
      </div>
      <p class="hero-note" data-download-note>{esc(t['hero_note'])} <a href="{url(lang, 'download')}">{esc(t['cta_all_systems'])}</a></p>
    </div>
    <div class="stage">
      <div class="stage-canvas">
        <div class="platform" aria-hidden="true"></div>
        <canvas id="mascot" data-skin="/assets/img/mascot.png" tabindex="0" role="img" aria-label="{esc(t['mascot_label'])}"></canvas>
        <p class="stage-hint" aria-hidden="true">{esc(t['mascot_hint'])}</p>
      </div>
      <form class="tryon" autocomplete="off">
        <label for="nick">{esc(t['tryon_label'])}</label>
        <div class="tryon-row">
          <input id="nick" name="nick" type="text" inputmode="text" maxlength="16" spellcheck="false" placeholder="{esc(t['tryon_placeholder'])}">
          <button class="btn btn-primary btn-small" type="submit">{esc(t['tryon_button'])}</button>
        </div>
        <p class="tryon-status" aria-live="polite"></p>
      </form>
    </div>
  </div>
</section>

<section class="section" id="video" aria-labelledby="video-title">
  <div class="wrap">
    <div class="section-head">
      <h2 id="video-title">{esc(t['video_title'])}</h2>
      <p class="lead">{esc(t['video_lead'])}</p>
    </div>
    <div class="frame video-frame">
      <video data-autoplay muted loop playsinline preload="none" width="1440" height="900" poster="/assets/video/prixum-{shots}-poster.webp" aria-label="{esc(t['video_label'])}">
        <source src="/assets/video/prixum-{shots}.mp4" type="video/mp4">
      </video>
    </div>
  </div>
</section>

<section class="section" id="features" aria-labelledby="features-title">
  <div class="wrap">
    <div class="section-head">
      <h2 id="features-title">{esc(t['features_title'])}</h2>
      <p class="lead">{esc(t['features_lead'])}</p>
    </div>
    {feature('f_skins', '<div class="frame">' + picture(shots, 'skins', t['f_skins_alt']) + '</div>')}
    {feature('f_glass', '<div class="frame">' + picture(shots, 'glass', t['f_glass_alt']) + '</div>', flip=True)}
    {feature('f_themes', stack)}
    {feature('f_settings', '<div class="frame">' + picture(shots, 'settings-search', t['f_settings_alt']) + '</div>', flip=True)}
    <h3 class="more-title">{esc(t['more_title'])}</h3>
    <ul class="more-grid">{more_items}</ul>
  </div>
</section>

<section class="section" id="compare" aria-labelledby="compare-title">
  <div class="wrap">
    <div class="section-head">
      <h2 id="compare-title">{esc(t['compare_title'])}</h2>
      <p class="lead">{esc(t['compare_lead'])}</p>
    </div>
    <div class="frame">
      <div class="compare">
        {picture(shots, 'prism', t['compare_left'], '(max-width: 1240px) 100vw, 1200px')}
        <div class="after">{picture(shots, 'main', t['compare_right'], '(max-width: 1240px) 100vw, 1200px')}</div>
        <span class="tag left" aria-hidden="true">{esc(t['compare_left'])}</span>
        <span class="tag right" aria-hidden="true">{esc(t['compare_right'])}</span>
        <div class="divider" aria-hidden="true"></div>
        <input type="range" min="0" max="100" value="50" aria-label="{esc(t['compare_label'])}">
        <div class="knob" aria-hidden="true">{ICONS['arrows']}</div>
      </div>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="cta-title">
  <div class="wrap">
    <div class="cta-panel">
      <h2 id="cta-title">{esc(t['cta_title'])}</h2>
      <p class="lead">{esc(t['cta_text'])}</p>
      <div class="cta-row">
        {download_button(lang)}
        <a class="btn btn-glass" href="{TELEGRAM}">{ICONS['telegram']}<span>{esc(t['cta_telegram'])}</span></a>
      </div>
    </div>
  </div>
</section>
</main>
"""
    return head(lang, "home", t["home_title"], t["home_description"], release) + nav(lang, "home") + body + footer(lang, "home", page_data(lang, release, releases))


def download(lang, release, releases):
    t = T[lang]
    v = release["tag_name"]
    sizes = {a["name"]: a["size"] for a in release.get("assets", [])}

    def file_button(key, kind):
        name = FILES[key].replace("{v}", v)
        size = f"{max(1, round(sizes[name] / 1048576))} {UNITS[lang]}" if name in sizes else ""
        return (f'<a class="btn btn-glass file-btn" data-file="{key}" href="https://github.com/{REPO}/releases/download/{v}/{name}">'
                f'{ICONS["download"]}<span>{esc(t[kind])}</span><small>{size}</small></a>')

    def variant(label, buttons):
        return f'<div class="variant"><span class="variant-name">{esc(label)}</span><div class="files">{"".join(buttons)}</div></div>'

    def card(os_key, icon, title, variants):
        return (f'<section class="os-card" data-os="{os_key}" aria-labelledby="os-{os_key}">'
                f'<div class="os-head">{ICONS[icon]}<h2 id="os-{os_key}">{esc(title)}</h2><span class="you-tag">{esc(t["your_system"])}</span></div>'
                f'{"".join(variants)}</section>')

    cards = "".join([
        card("windows", "windows", t["os_windows"], [
            variant(t["os_windows_x64"], [file_button("win-x64-setup", "kind_exe"), file_button("win-x64-portable", "kind_zip")]),
            variant(t["os_windows_arm"], [file_button("win-arm-setup", "kind_exe"), file_button("win-arm-portable", "kind_zip")]),
        ]),
        card("macos", "apple", t["os_macos"], [
            variant(t["os_macos_note"], [file_button("mac-dmg", "kind_dmg"), file_button("mac-portable", "kind_zip")]),
        ]),
        card("linux", "linux", t["os_linux"], [
            variant(t["os_linux_x64"], [file_button("linux-x64-appimage", "kind_appimage"), file_button("linux-x64-portable", "kind_targz")]),
            variant(t["os_linux_arm"], [file_button("linux-arm-appimage", "kind_appimage"), file_button("linux-arm-portable", "kind_targz")]),
        ]),
        card("arch", "arch", t["os_arch"], [
            variant(t["os_arch_note"], [file_button("arch-pkg", "kind_pkg")]),
        ]),
    ])
    release_url = f"{GITHUB}/releases/tag/{v}"
    pkg = FILES["arch-pkg"].replace("{v}", v)
    notes = "".join(f"<li>{t[k]}</li>" for k in ("note_unsigned_html", "note_portable_html", "note_mingw_html", "note_arch_html",
                                               "note_gamescope_html", "note_account_html"))
    notes = notes.replace("{release_url}", release_url).replace(f"{{pkg}}", pkg)
    notes = notes.replace(f'<a href="{release_url}">', f'<a href="{release_url}" data-release-url>').replace(
        f"<code>sudo pacman -U {pkg}</code>", f"<code data-pkg>sudo pacman -U {pkg}</code>")
    body = f"""<main id="main">
<section class="page-hero">
  <div class="wrap">
    <div class="section-head">
      <h1>{esc(t['download_title'])}</h1>
      <p class="lead">{esc(t['download_lead'])}</p>
    </div>
    <div class="dl-main">
      {download_button(lang)}
      <p class="dl-meta" data-release-line data-download-note>{esc(t['release_line'].format(version=v, date=fmt_date(release['published_at'], lang)))}</p>
      <a class="btn btn-glass btn-small" href="{GITHUB}/releases">{ICONS['github']}<span>{esc(t['all_versions'])}</span></a>
    </div>
  </div>
</section>
<section class="section" aria-label="{esc(t['files'])}" style="padding-top: 0">
  <div class="wrap">
    <div class="os-grid">{cards}</div>
    <h2 class="notes-title">{esc(t['notes_title'])}</h2>
    <ul class="notes">{notes}</ul>
  </div>
</section>
</main>
"""
    return head(lang, "download", t["download_title"], t["download_description"], release) + nav(lang, "download") + body + footer(lang, "download", page_data(lang, release, releases))


def changelog(lang, release, releases):
    t = T[lang]
    items = []
    for i, r in enumerate(releases):
        date = fmt_date(r["published_at"], lang)
        items.append(f"""<article class="release" id="v{esc(r['tag_name'])}">
  <div class="release-side">
    <span class="version">{esc(r['tag_name'])}</span>
    <time datetime="{r['published_at'][:10]}">{esc(t['release_from'].format(date=date))}</time>
    {'<span class="latest-tag">' + esc(t['latest']) + '</span>' if i == 0 else ''}
    <div class="release-links">
      <a class="btn btn-glass btn-small" href="{esc(r['html_url'])}">{ICONS['github']}<span>{esc(t['on_github'])}</span></a>
    </div>
  </div>
  <div class="prose">{r['notes'][lang]}</div>
</article>""")
    body = f"""<main id="main">
<section class="page-hero">
  <div class="wrap">
    <div class="section-head">
      <h1>{esc(t['changelog_title'])}</h1>
      <p class="lead">{esc(t['changelog_lead'])}</p>
    </div>
  </div>
</section>
<section class="section" style="padding-top: 0">
  <div class="wrap" data-releases>{''.join(items)}</div>
</section>
</main>
"""
    return head(lang, "changelog", f"{t['changelog_title']} — Prixum Launcher", t["changelog_description"], release) + nav(lang, "changelog") + body + footer(lang, "changelog", page_data(lang, release, releases))


def faq(lang, release, releases):
    t = T[lang]
    items = "".join(
        f'<details class="faq-item"><summary>{esc(q)}</summary><div class="faq-answer">{a.replace("{download}", url(lang, "download"))}</div></details>'
        for q, a in FAQ[lang]
    )
    schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in FAQ[lang]],
    }
    body = f"""<main id="main">
<section class="page-hero">
  <div class="wrap">
    <div class="section-head">
      <h1>{esc(t['faq_title'])}</h1>
      <p class="lead">{esc(t['faq_lead'])}</p>
    </div>
  </div>
</section>
<section class="section" style="padding-top: 0">
  <div class="wrap">
    <div class="faq-list">{items}</div>
  </div>
</section>
<section class="section" style="padding-top: 0">
  <div class="wrap">
    <div class="cta-panel">
      <h2>{esc(t['faq_more_title'])}</h2>
      <p class="lead">{esc(t['faq_more_text'])}</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="{TELEGRAM}">{ICONS['telegram']}<span>{esc(t['cta_telegram'])}</span></a>
        <a class="btn btn-glass" href="{GITHUB}/issues">{ICONS['github']}<span>{esc(t['report_bug'])}</span></a>
      </div>
    </div>
  </div>
</section>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</main>
"""
    return head(lang, "faq", f"{t['faq_title']} — Prixum Launcher", t["faq_description"], release) + nav(lang, "faq") + body + footer(lang, "faq", page_data(lang, release, releases))


def not_found(release, releases):
    lang = "ru"
    t = T[lang]
    body = f"""<main id="main">
<section class="page-hero">
  <div class="wrap">
    <div class="section-head">
      <h1>{esc(t['not_found_title'])}</h1>
      <p class="lead">{esc(t['not_found_text'])} {esc(T['en']['not_found_title'])}.</p>
      <div class="cta-row"><a class="btn btn-primary" href="/">{esc(t['not_found_home'])}</a><a class="btn btn-glass" href="/en/">{esc(T['en']['not_found_home'])}</a></div>
    </div>
  </div>
</section>
</main>
"""
    page = head(lang, "home", t["not_found_title"], t["not_found_text"], release) + nav(lang, "home") + body + footer(lang, "home", page_data(lang, release, releases))
    # the error page is served for any address, its own links must not point at itself
    return page.replace('<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="x-canonical"', 1)


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)


def main():
    refresh = "--refresh" in sys.argv
    build_assets()
    releases = load_releases(refresh)
    latest = releases[0]
    for lang in LANGS:
        base = PREFIX[lang].lstrip("/")
        write(os.path.join(base, "index.html"), home(lang, latest, releases))
        write(os.path.join(base, "download", "index.html"), download(lang, latest, releases))
        write(os.path.join(base, "changelog", "index.html"), changelog(lang, latest, releases))
        write(os.path.join(base, "faq", "index.html"), faq(lang, latest, releases))
    write("404.html", not_found(latest, releases))
    urls = []
    for page in PAGES:
        for lang in LANGS:
            links = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{url(l, page)}"/>' for l in LANGS)
            urls.append(f"<url><loc>{SITE}{url(lang, page)}</loc>{links}</url>")
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print("built", sum(len(files) for _, _, files in os.walk(OUT)), "files into", OUT)


if __name__ == "__main__":
    main()
