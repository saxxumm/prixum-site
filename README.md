# prixum.org

Сайт [Prixum Launcher](https://github.com/saxxumm/PrixumLauncher): главная, «Скачать», «Что нового» и FAQ
на русском, английском и украинском. Собирается в `docs/` и публикуется через GitHub Pages на prixum.org.

```bash
python3 build.py            # собрать docs/
python3 build.py --refresh  # сначала забрать свежий список релизов с GitHub (нужен gh)
```

- `src/i18n.py` — все тексты сайта на трёх языках и FAQ.
- `src/assets` — стили, скрипты (рендер скинов `skinview.js` и `site.js`), картинки, видео.
- `src/shots/<язык>` — скриншоты лаунчера, `src/releases` — релизы и переводы заметок к ним.
- `tools/sandbox` — песочница, в которой лаунчер снимается для сайта: `shoot.py ru` делает скриншоты и видео.
- `tools/mascot` — исходный скин маскота и скрипт, который добавляет к нему детали Prixum.
