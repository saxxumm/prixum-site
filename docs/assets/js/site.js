/* prixum.org: theme switch, menu, sakura petals, the walking mascot, the download for this computer, the comparison
 * slider, the video and fresh releases. Every part checks for its elements, so one script serves every page. */
(() => {
  "use strict";

  const data = JSON.parse(document.getElementById("site-data").textContent);
  const S = data.strings;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } },
  };
  const fill = (text, values) => text.replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : `{${key}}`));

  /* ---------- theme and menu ---------- */
  const themeButton = document.querySelector(".theme-btn");
  function syncThemeLabel() {
    if (!themeButton) return;
    const light = document.documentElement.dataset.theme === "light";
    themeButton.setAttribute("aria-label", light ? S.theme_dark : S.theme_light);
    themeButton.title = themeButton.getAttribute("aria-label");
  }
  syncThemeLabel();
  themeButton?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    store.set("theme", next);
    syncThemeLabel();
    document.dispatchEvent(new Event("themechange"));
  });

  const nav = document.querySelector(".nav");
  const menuButton = document.querySelector(".menu-btn");
  menuButton?.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("click", (event) => {
    if (nav?.classList.contains("open") && !nav.contains(event.target)) {
      nav.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
    }
    const lang = document.querySelector(".lang[open]");
    if (lang && !lang.contains(event.target)) lang.open = false;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    nav?.classList.remove("open");
    menuButton?.setAttribute("aria-expanded", "false");
    const lang = document.querySelector(".lang[open]");
    if (lang) lang.open = false;
  });
  // a language picked by hand wins over the browser language from now on
  for (const link of document.querySelectorAll("[data-lang-link]")) {
    link.addEventListener("click", () => store.set("lang", link.dataset.langLink));
  }

  /* ---------- sakura petals ---------- */
  const petalCanvas = document.getElementById("petals");
  if (petalCanvas) {
    const ctx = petalCanvas.getContext("2d");
    let petals = [];
    let width = 0, height = 0, ratio = 1, frame = 0, last = 0;
    const colors = () => {
      const style = getComputedStyle(document.documentElement);
      return [style.getPropertyValue("--petal-a").trim(), style.getPropertyValue("--petal-b").trim()];
    };
    let palette = colors();
    document.addEventListener("themechange", () => { palette = colors(); });
    const spawn = (anywhere) => ({
      x: Math.random() * width,
      y: anywhere ? Math.random() * height : -20,
      size: 7 + Math.random() * 7,
      fall: 14 + Math.random() * 18,
      drift: 8 + Math.random() * 14,
      phase: Math.random() * Math.PI * 2,
      spin: (Math.random() - 0.5) * 1.2,
      angle: Math.random() * Math.PI * 2,
      tone: Math.random() < 0.5 ? 0 : 1,
      alpha: 0.35 + Math.random() * 0.35,
    });
    function resize() {
      ratio = Math.min(2, window.devicePixelRatio || 1);
      width = window.innerWidth;
      height = window.innerHeight;
      petalCanvas.width = Math.round(width * ratio);
      petalCanvas.height = Math.round(height * ratio);
      const count = Math.round(Math.min(26, Math.max(10, width / 60)));
      while (petals.length < count) petals.push(spawn(true));
      petals.length = count;
    }
    function petal(p) {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.angle);
      ctx.scale(1, 0.62 + 0.38 * Math.sin(p.phase * 1.7));
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = palette[p.tone];
      ctx.beginPath();
      // a sakura petal: round body with a small notch at the tip
      ctx.moveTo(0, -p.size);
      ctx.bezierCurveTo(p.size * 0.95, -p.size * 0.7, p.size * 0.8, p.size * 0.7, 0, p.size);
      ctx.bezierCurveTo(-p.size * 0.8, p.size * 0.7, -p.size * 0.95, -p.size * 0.7, -p.size * 0.18, -p.size * 0.92);
      ctx.lineTo(0, -p.size * 0.72);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
    function tick(time) {
      frame = 0;
      const dt = last ? Math.min(0.05, (time - last) / 1000) : 0;
      last = time;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      for (const p of petals) {
        p.phase += dt;
        p.y += p.fall * dt;
        p.x += Math.sin(p.phase) * p.drift * dt;
        p.angle += p.spin * dt;
        if (p.y > height + 20) Object.assign(p, spawn(false));
        petal(p);
      }
      if (!document.hidden && !still.matches) frame = requestAnimationFrame(tick);
    }
    const start = () => {
      if (still.matches) {
        ctx.clearRect(0, 0, petalCanvas.width, petalCanvas.height);
        return;
      }
      if (!frame && !document.hidden) { last = 0; frame = requestAnimationFrame(tick); }
    };
    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", start);
    still.addEventListener("change", start);
    start();
  }

  /* ---------- the walking mascot and trying on a skin ---------- */
  const mascotCanvas = document.getElementById("mascot");
  if (mascotCanvas && typeof SkinView !== "undefined") {
    const glowCanvas = document.createElement("canvas");
    const mascot = new Image();
    let skin = mascot, slim = true, yaw = -24, drag = null, began = performance.now(), frame = 0, onScreen = true;
    let glow = getComputedStyle(document.documentElement).getPropertyValue("--mascot-glow").trim();
    document.addEventListener("themechange", () => {
      glow = getComputedStyle(document.documentElement).getPropertyValue("--mascot-glow").trim();
      if (still.matches) draw(performance.now());
    });
    mascot.src = mascotCanvas.dataset.skin;

    function draw(now) {
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      const w = mascotCanvas.clientWidth, h = mascotCanvas.clientHeight;
      if (!w || !h || !skin.width) return;
      if (mascotCanvas.width !== Math.round(w * ratio)) { mascotCanvas.width = Math.round(w * ratio); mascotCanvas.height = Math.round(h * ratio); }
      glowCanvas.width = mascotCanvas.width;
      glowCanvas.height = mascotCanvas.height;
      const t = (now - began) / 1000;
      const moving = !still.matches;
      // turns a little by itself while nobody drags it
      const sway = drag || !moving ? 0 : Math.sin(t * 0.35) * 14;
      const g = glowCanvas.getContext("2d");
      g.setTransform(ratio, 0, 0, ratio, 0, 0);
      SkinView.paint(g, { x: 0, y: h * 0.07, width: w, height: h * 0.8 }, skin, slim, {
        yaw: yaw + sway, pitch: 9, walk: moving ? t * 4.2 : 0, stride: moving ? 1 : 0, idle: moving ? t * 1.4 : 0,
      });
      const ctx = mascotCanvas.getContext("2d");
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, mascotCanvas.width, mascotCanvas.height);
      ctx.filter = `drop-shadow(0 0 ${Math.round(14 * ratio)}px ${glow})`;
      ctx.drawImage(glowCanvas, 0, 0);
      ctx.filter = "none";
    }
    function loop(now) {
      frame = 0;
      draw(now);
      if (!still.matches && onScreen && !document.hidden) frame = requestAnimationFrame(loop);
    }
    const run = () => { if (!frame) frame = requestAnimationFrame(loop); };
    mascot.addEventListener("load", run);
    new IntersectionObserver((entries) => { onScreen = entries[0].isIntersecting; if (onScreen) run(); }).observe(mascotCanvas);
    document.addEventListener("visibilitychange", run);
    still.addEventListener("change", run);
    window.addEventListener("resize", () => draw(performance.now()));

    mascotCanvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, yaw }; mascotCanvas.setPointerCapture(e.pointerId); });
    mascotCanvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      yaw = drag.yaw + (e.clientX - drag.x) * 0.7;
      if (still.matches) draw(performance.now());
    });
    const release = () => { drag = null; };
    mascotCanvas.addEventListener("pointerup", release);
    mascotCanvas.addEventListener("pointercancel", release);
    mascotCanvas.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        yaw += e.key === "ArrowLeft" ? -15 : 15;
        if (still.matches) draw(performance.now());
        e.preventDefault();
      }
    });

    const form = document.querySelector(".tryon");
    const status = document.querySelector(".tryon-status");
    const say = (text, withReset) => {
      status.textContent = text;
      if (withReset) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = S.tryon_reset;
        button.addEventListener("click", () => {
          skin = mascot;
          slim = true;
          status.textContent = "";
          form.querySelector("input").value = "";
          draw(performance.now());
        });
        status.append(" ", button);
      }
    };
    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = form.querySelector("input").value.trim();
      if (!/^[A-Za-z0-9_]{3,16}$/.test(name)) {
        say(S.tryon_bad_name);
        return;
      }
      say(S.tryon_loading);
      const image = new Image();
      image.crossOrigin = "anonymous";
      image.onload = () => {
        try {
          skin = SkinView.normalize(image);
          slim = SkinView.isSlim(skin);
          say(fill(S.tryon_done, { name }), true);
          draw(performance.now());
        } catch (e) {
          say(S.tryon_failed);
        }
      };
      image.onerror = () => say(S.tryon_failed);
      image.src = `https://mc-heads.net/skin/${encodeURIComponent(name)}`;
    });
  }

  /* ---------- the download for this computer ---------- */
  const release = data.release;
  function detect() {
    const ua = navigator.userAgent || "";
    const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
    const all = `${platform} ${ua}`;
    if (/Android|iPhone|iPad|iPod/i.test(ua)) return Promise.resolve({ mobile: true });
    let arm = /aarch64|arm64|armv8/i.test(all);
    const finish = () => {
      if (/Win/i.test(all)) return { os: "windows", key: arm ? "win-arm-setup" : "win-x64-setup", card: "windows", variant: arm ? "arm" : "x64" };
      if (/Mac/i.test(all)) return { os: "macos", key: "mac-dmg", card: "macos" };
      if (/Linux|X11|CrOS/i.test(all)) return { os: "linux", key: arm ? "linux-arm-appimage" : "linux-x64-appimage", card: "linux", variant: arm ? "arm" : "x64" };
      return {};
    };
    if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
      return navigator.userAgentData.getHighEntropyValues(["architecture"])
        .then((hints) => { if (hints.architecture) arm = hints.architecture === "arm"; return finish(); })
        .catch(finish);
    }
    return Promise.resolve(finish());
  }
  const fileName = (key) => release.files[key].replace(/\{v\}/g, release.version);
  const fileUrl = (key) => `https://github.com/${data.repo}/releases/download/${release.version}/${fileName(key)}`;
  const megabytes = (bytes) => `${Math.max(1, Math.round(bytes / 1048576))} ${S.mb}`;
  const formatDate = (iso) => {
    try {
      return new Intl.DateTimeFormat(data.locale, { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso)).replace(/\s?(г\.|р\.)$/, "");
    } catch (e) { return ""; }
  };
  let system = null;

  function renderDownloads() {
    for (const link of document.querySelectorAll("[data-file]")) {
      const key = link.dataset.file;
      link.href = fileUrl(key);
      const size = link.querySelector("small");
      const bytes = release.sizes[fileName(key)];
      if (size && bytes) size.textContent = megabytes(bytes);
    }
    for (const el of document.querySelectorAll("[data-release-line]")) {
      el.textContent = fill(S.release_line, { version: release.version, date: formatDate(release.date) });
    }
    for (const el of document.querySelectorAll("[data-version]")) el.textContent = release.version;
    for (const link of document.querySelectorAll("[data-release-url]")) link.href = `https://github.com/${data.repo}/releases/tag/${release.version}`;
    for (const el of document.querySelectorAll("[data-pkg]")) el.textContent = `sudo pacman -U ${fileName("arch-pkg")}`;
    for (const button of document.querySelectorAll("[data-download-main]")) {
      const label = button.querySelector("span");
      if (system && system.key) {
        button.href = fileUrl(system.key);
        label.textContent = fill(S.cta_download_for, { os: S[`os_${system.os}`] });
      } else {
        button.href = button.dataset.fallback;
        label.textContent = S.cta_download;
      }
    }
    for (const note of document.querySelectorAll("[data-download-note]")) {
      if (system && system.mobile) note.textContent = S.mobile_note;
    }
    for (const card of document.querySelectorAll(".os-card")) {
      card.classList.toggle("you", Boolean(system && system.card === card.dataset.os));
    }
  }
  if (document.querySelector("[data-file], [data-download-main]")) {
    renderDownloads();
    detect().then((result) => { system = result; renderDownloads(); });
    // the newest release updates the links by itself, without the API the page keeps what it was built with
    fetch(`https://api.github.com/repos/${data.repo}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((latest) => {
        if (!/^\d+\.\d+\.\d+$/.test(latest.tag_name || "")) return;
        release.version = latest.tag_name;
        release.date = latest.published_at || release.date;
        for (const asset of latest.assets || []) release.sizes[asset.name] = asset.size;
        renderDownloads();
      })
      .catch(() => {});
  }

  /* ---------- comparison slider ---------- */
  for (const compare of document.querySelectorAll(".compare")) {
    const range = compare.querySelector("input[type=range]");
    const set = () => compare.style.setProperty("--pos", `${range.value}%`);
    range.addEventListener("input", set);
    set();
  }

  /* ---------- the video plays while it is on screen ---------- */
  for (const video of document.querySelectorAll("video[data-autoplay]")) {
    if (still.matches) {
      video.controls = true;
      continue;
    }
    new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) video.play().catch(() => { video.controls = true; });
      else video.pause();
    }, { threshold: 0.35 }).observe(video);
  }

  /* ---------- releases newer than this page ---------- */
  const list = document.querySelector("[data-releases]");
  if (list) {
    fetch(`https://api.github.com/repos/${data.repo}/releases?per_page=10`, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((releases) => {
        const known = new Set(data.known_releases);
        const fresh = releases.filter((r) => !r.draft && !known.has(r.tag_name));
        if (!fresh.length) return;
        return new Promise((resolve, reject) => {
          if (window.marked) return resolve();
          const script = document.createElement("script");
          script.src = "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js";
          script.onload = resolve;
          script.onerror = reject;
          document.head.append(script);
        }).then(() => {
          for (const r of fresh.reverse()) {
            const article = document.createElement("article");
            article.className = "release";
            const body = pickLanguage(r.body || "", data.lang);
            article.innerHTML = `<div class="release-side"><span class="version"></span><time></time></div><div class="prose"></div>`;
            article.querySelector(".version").textContent = r.tag_name;
            article.querySelector("time").textContent = formatDate(r.published_at);
            article.querySelector(".prose").innerHTML = window.marked.parse(body);
            list.prepend(article);
          }
          list.querySelector(".latest-tag")?.remove();
        });
      })
      .catch(() => {});
  }
  // release notes: Russian first, then <details> sections named English and Українська
  function pickLanguage(body, lang) {
    const sections = { en: /<details>\s*<summary>\s*English\s*<\/summary>([\s\S]*?)<\/details>/i, uk: /<details>\s*<summary>\s*Українська\s*<\/summary>([\s\S]*?)<\/details>/i };
    let text = body;
    if (sections[lang]) {
      const match = body.match(sections[lang]);
      if (match) text = match[1];
    }
    text = text.replace(/<details>[\s\S]*?<\/details>/gi, "");
    return text.split(/\n## (Какой файл скачать|Which file to download|Який файл завантажити)/)[0].trim();
  }
})();
