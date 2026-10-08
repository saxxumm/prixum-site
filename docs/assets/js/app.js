/*
 * SkinView: a Minecraft player drawn with the canvas 2D API, ported from Prixum Launcher's SkinRenderer.
 * Under an orthographic camera every face of the model is a parallelogram, so it is an affine transform of its
 * texture rectangle. No WebGL, and the pixels stay sharp.
 */
const SkinView = (() => {
  "use strict";

  const point = (x, y, z) => new DOMPoint(x, y, z);

  function rotation(pivot, angle, axis) {
    return new DOMMatrix()
      .translate(pivot[0], pivot[1], pivot[2])
      .rotateAxisAngle(axis[0], axis[1], axis[2], angle)
      .translate(-pivot[0], -pivot[1], -pivot[2]);
  }

  // the six faces of a box with the texture layout Minecraft uses for every part
  function addBox(faces, box, view) {
    const g = box.grow || 0;
    const [x0, y0, z0] = box.min.map((v) => v - g);
    const [x1, y1, z1] = box.max.map((v) => v + g);
    const [w, h, d] = box.size;
    const [u, v] = box.uv;
    const s = box.texel || 1;
    const m = view.multiply(box.pose);
    const add = (tl, tr, bl, rect) =>
      faces.push({
        tl: m.transformPoint(point(...tl)),
        tr: m.transformPoint(point(...tr)),
        bl: m.transformPoint(point(...bl)),
        rect: rect.map((value) => value * s),
        image: box.image,
      });
    add([x0, y1, z1], [x1, y1, z1], [x0, y0, z1], [u + d, v + d, w, h]); // front
    add([x1, y1, z0], [x0, y1, z0], [x1, y0, z0], [u + d + w + d, v + d, w, h]); // back
    add([x0, y1, z0], [x0, y1, z1], [x0, y0, z0], [u, v + d, d, h]); // right side of the player
    add([x1, y1, z1], [x1, y1, z0], [x1, y0, z1], [u + d + w, v + d, d, h]); // left side of the player
    add([x0, y1, z0], [x1, y1, z0], [x0, y1, z1], [u + d, v, w, d]); // top
    add([x0, y0, z1], [x1, y0, z1], [x0, y0, z0], [u + d + w, v, w, d]); // bottom
  }

  /**
   * Paints the player as large as fits into the rectangle, centered.
   * pose: yaw and pitch in degrees, walk in radians (one step per pi), stride 0..1, idle in radians.
   */
  function paint(ctx, rect, skin, slim, pose = {}, cape = null) {
    if (!skin || !rect.width || !rect.height) return;
    const { yaw = -28, pitch = 12, walk = 0, stride = 0, idle = 0 } = pose;
    const swing = Math.sin(walk) * stride;
    const legAngle = 34 * swing;
    const armAngle = -30 * swing;
    // arms drift away from the body a little while standing
    const armSpread = 2.5 + 1.5 * Math.sin(idle);
    const bob = 0.6 * stride * Math.abs(Math.cos(walk));

    const body = new DOMMatrix().translate(0, bob, 0);
    const armWidth = slim ? 3 : 4;
    const rightArm = body
      .multiply(rotation([-4 - armWidth / 2, 22, 0], armAngle, [1, 0, 0]))
      .multiply(rotation([-4, 24, 0], -armSpread, [0, 0, 1]));
    const leftArm = body
      .multiply(rotation([4 + armWidth / 2, 22, 0], -armAngle, [1, 0, 0]))
      .multiply(rotation([4, 24, 0], armSpread, [0, 0, 1]));
    const rightLeg = rotation([-2, 12, 0], legAngle, [1, 0, 0]);
    const leftLeg = rotation([2, 12, 0], -legAngle, [1, 0, 0]);

    const view = new DOMMatrix().rotateAxisAngle(1, 0, 0, pitch).rotateAxisAngle(0, 1, 0, yaw);

    const faces = [];
    const part = (min, max, uv, overlayUv, size, grow, partPose) => {
      addBox(faces, { min, max, uv, size, pose: partPose, image: skin }, view);
      addBox(faces, { min, max, uv: overlayUv, size, grow, pose: partPose, image: skin }, view);
    };
    part([-4, 24, -4], [4, 32, 4], [0, 0], [32, 0], [8, 8, 8], 0.5, body);
    part([-4, 12, -2], [4, 24, 2], [16, 16], [16, 32], [8, 12, 4], 0.25, body);
    part([-4 - armWidth, 12, -2], [-4, 24, 2], [40, 16], [40, 32], [armWidth, 12, 4], 0.25, rightArm);
    part([4, 12, -2], [4 + armWidth, 24, 2], [32, 48], [48, 48], [armWidth, 12, 4], 0.25, leftArm);
    part([-4, 0, -2], [0, 12, 2], [0, 16], [0, 32], [4, 12, 4], 0.25, rightLeg);
    part([0, 0, -2], [4, 12, 2], [16, 48], [0, 48], [4, 12, 4], 0.25, leftLeg);

    if (cape) {
      // hangs from the shoulders and lifts while walking
      const lift = 6 + 12 * stride * (0.6 + 0.4 * Math.sin(walk * 2)) + 1.5 * Math.sin(idle);
      const capePose = body.multiply(rotation([0, 24, -2], lift, [1, 0, 0]));
      addBox(faces, { min: [-5, 8, -3], max: [5, 24, -2], uv: [0, 0], size: [10, 16, 1], pose: capePose, image: cape, texel: cape.width / 64 }, view);
    }

    // facing the viewer and back to front, the overlay sits just outside its part so it wins ties
    const visible = [];
    for (const face of faces) {
      const ax = face.bl.x - face.tl.x, ay = face.bl.y - face.tl.y;
      const bx = face.tr.x - face.tl.x, by = face.tr.y - face.tl.y;
      const normalZ = ax * by - ay * bx;
      if (normalZ <= 1e-4) continue;
      const brz = face.tr.z + face.bl.z - face.tl.z;
      face.depth = (face.tl.z + face.tr.z + face.bl.z + brz) / 4;
      visible.push(face);
    }
    visible.sort((a, b) => a.depth - b.depth);

    // the same scale for every pose, so a walking player does not pulse
    const scale = Math.min(rect.height / 37, rect.width / 24);
    const ox = rect.x + rect.width / 2;
    const oy = rect.y + rect.height / 2 + 16.5 * scale;
    const project = (p) => [ox + p.x * scale, oy - p.y * scale];

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    const base = ctx.getTransform();
    for (const face of visible) {
      const [tx, ty] = project(face.tl);
      const [rx, ry] = project(face.tr);
      const [bx, by] = project(face.bl);
      const [, , tw, th] = face.rect;
      const ux = (rx - tx) / tw, uy = (ry - ty) / tw;
      const vx = (bx - tx) / th, vy = (by - ty) / th;
      ctx.setTransform(base.multiply(new DOMMatrix([ux, uy, vx, vy, tx, ty])));
      // a third of a screen pixel of overlap hides the seams between faces
      const lu = Math.hypot(ux, uy), lv = Math.hypot(vx, vy);
      const gu = lu > 0 ? 0.35 / lu : 0, gv = lv > 0 ? 0.35 / lv : 0;
      ctx.drawImage(face.image, face.rect[0], face.rect[1], tw, th, -gu, -gv, tw + 2 * gu, th + 2 * gv);
    }
    ctx.restore();
  }

  /** slim skins leave the outer column of the arm texture empty */
  function isSlim(image) {
    const c = document.createElement("canvas");
    c.width = 64;
    c.height = 64;
    const g = c.getContext("2d");
    g.drawImage(image, 0, 0);
    return g.getImageData(54, 20, 1, 1).data[3] === 0;
  }

  /** old 64x32 skins have no left arm and leg of their own, Minecraft mirrors the right ones */
  function normalize(image) {
    if (image.height !== 32) return image;
    const c = document.createElement("canvas");
    c.width = 64;
    c.height = 64;
    const g = c.getContext("2d");
    g.imageSmoothingEnabled = false;
    g.drawImage(image, 0, 0);
    const mirror = (sx, sy, w, h, dx, dy) => {
      g.save();
      g.translate(dx + w, dy);
      g.scale(-1, 1);
      g.drawImage(image, sx, sy, w, h, 0, 0, w, h);
      g.restore();
    };
    // leg and arm boxes: top and bottom, then the four sides with right and left swapped
    for (const [sx, sy, dx, dy] of [[0, 16, 16, 48], [40, 16, 32, 48]]) {
      mirror(sx + 4, sy, 4, 4, dx + 4, dy);
      mirror(sx + 8, sy, 4, 4, dx + 8, dy);
      mirror(sx, sy + 4, 4, 12, dx + 8, dy + 4);
      mirror(sx + 4, sy + 4, 4, 12, dx + 4, dy + 4);
      mirror(sx + 8, sy + 4, 4, 12, dx, dy + 4);
      mirror(sx + 12, sy + 4, 4, 12, dx + 12, dy + 4);
    }
    return c;
  }

  return { paint, isSlim, normalize };
})();

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
  // Petals are drawn once into small sprites (front and back, two tints, sharp and out of focus) and then only moved:
  // each one tumbles in 3D (the width follows the cosine of its flip, the back side shows when it turns over), sways,
  // rides a wind with slow gusts, drifts with the page at its own depth and gets blown aside by the mouse.
  const petalCanvas = document.getElementById("petals");
  if (petalCanvas) {
    const ctx = petalCanvas.getContext("2d");
    const SPRITE = 64; // petal height in sprite pixels
    let sprites = null, tint = 1;
    let petals = [];
    let width = 0, height = 0, ratio = 1, frame = 0, last = 0, clock = 0, scroll = window.scrollY;
    let gust = { start: 8, length: 3.5, power: 0 };
    const mouse = { x: -1e4, y: -1e4, vx: 0, vy: 0, at: 0 };

    // half a petal, tip (with the notch) at the top, the narrow base at the bottom; x and y in petal heights
    function outline(g, h) {
      const p = (x, y) => [x * h, y * h];
      g.beginPath();
      g.moveTo(...p(0, 0.14));
      g.bezierCurveTo(...p(0.07, 0.02), ...p(0.29, -0.02), ...p(0.39, 0.1));
      g.bezierCurveTo(...p(0.49, 0.22), ...p(0.45, 0.48), ...p(0.3, 0.7));
      g.bezierCurveTo(...p(0.2, 0.84), ...p(0.07, 0.97), ...p(0, 1));
      g.bezierCurveTo(...p(-0.07, 0.97), ...p(-0.2, 0.84), ...p(-0.3, 0.7));
      g.bezierCurveTo(...p(-0.45, 0.48), ...p(-0.49, 0.22), ...p(-0.39, 0.1));
      g.bezierCurveTo(...p(-0.29, -0.02), ...p(-0.07, 0.02), ...p(0, 0.14));
      g.closePath();
    }
    function sprite(colors, back, blur) {
      const pad = Math.ceil(blur * 2.5) + 2;
      const canvas = document.createElement("canvas");
      canvas.width = Math.ceil(SPRITE) + pad * 2;
      canvas.height = SPRITE + pad * 2;
      const g = canvas.getContext("2d");
      if (blur) g.filter = `blur(${blur}px)`;
      g.translate(canvas.width / 2, pad);
      const fill = g.createLinearGradient(0, 0, 0, SPRITE);
      fill.addColorStop(0, back ? colors.mid : colors.light);
      fill.addColorStop(0.55, colors.mid);
      fill.addColorStop(1, colors.deep);
      outline(g, SPRITE);
      g.fillStyle = fill;
      g.fill();
      g.save();
      g.clip();
      if (back) {
        g.fillStyle = "rgba(70, 0, 40, 0.14)";
        g.fillRect(-SPRITE, 0, SPRITE * 2, SPRITE);
      } else {
        const shine = g.createRadialGradient(-0.12 * SPRITE, 0.32 * SPRITE, 0, -0.12 * SPRITE, 0.32 * SPRITE, 0.42 * SPRITE);
        shine.addColorStop(0, "rgba(255, 255, 255, 0.45)");
        shine.addColorStop(1, "rgba(255, 255, 255, 0)");
        g.fillStyle = shine;
        g.fillRect(-SPRITE, 0, SPRITE * 2, SPRITE);
        if (!blur) {
          g.strokeStyle = "rgba(255, 255, 255, 0.4)";
          g.lineWidth = 1.3;
          g.lineCap = "round";
          for (const side of [-1, 0, 1]) {
            g.beginPath();
            g.moveTo(0, 0.93 * SPRITE);
            g.quadraticCurveTo(side * 0.08 * SPRITE, 0.6 * SPRITE, side * 0.2 * SPRITE, (side ? 0.3 : 0.26) * SPRITE);
            g.stroke();
          }
        }
      }
      g.restore();
      return { canvas, x: canvas.width / 2, y: pad + SPRITE * 0.55 };
    }
    function paint() {
      const style = getComputedStyle(document.documentElement);
      const token = (name) => style.getPropertyValue(name).trim();
      const pale = { light: token("--petal-light"), mid: token("--petal-mid"), deep: token("--petal-deep") };
      const rosy = { light: token("--petal-mid"), mid: token("--petal-mid"), deep: token("--petal-deep") };
      tint = parseFloat(token("--petal-alpha")) || 0.8;
      // sprites[tone][back][soft]
      sprites = [pale, rosy].map((colors) => [false, true].map((back) => [0, 5].map((blur) => sprite(colors, back, blur))));
    }
    const spawn = (p, anywhere) => {
      p.x = anywhere ? Math.random() * width : Math.random() * (width * 1.15) - width * 0.15;
      p.y = anywhere ? Math.random() * height : -30 - Math.random() * 60;
      p.vx = 0;
      p.vy = 0;
      p.fall = 18 + Math.random() * 14;
      p.drift = 10 + Math.random() * 16;
      p.phase = Math.random() * Math.PI * 2;
      p.angle = Math.random() * Math.PI * 2;
      p.spin = (Math.random() - 0.5) * 1.6;
      p.flip = Math.random() * Math.PI * 2;
      p.flipSpeed = 1.1 + Math.random() * 1.6;
      p.tone = Math.random() < 0.55 ? 0 : 1;
      return p;
    };
    function petal() {
      const z = 0.5 + Math.pow(Math.random(), 1.6) * 1.1; // mostly far and small, a few close and out of focus
      const soft = z > 1.35;
      return spawn({ z, soft, size: (6 + 14 * z) * (soft ? 1.3 : 1), alpha: soft ? 0.62 : 0.5 + 0.45 * Math.min(1, (z - 0.5) / 0.7) }, true);
    }
    function resize() {
      ratio = Math.min(2, window.devicePixelRatio || 1);
      width = window.innerWidth;
      height = window.innerHeight;
      petalCanvas.width = Math.round(width * ratio);
      petalCanvas.height = Math.round(height * ratio);
      const count = Math.round(Math.min(42, Math.max(14, (width * height) / 36000)));
      while (petals.length < count) petals.push(petal());
      petals.length = count;
      petals.sort((a, b) => a.z - b.z);
    }
    function wind(t) {
      if (t > gust.start + gust.length) {
        gust = { start: t + 9 + Math.random() * 12, length: 2.5 + Math.random() * 2.5, power: 35 + Math.random() * 35 };
      }
      const g = t > gust.start ? Math.sin((Math.PI * (t - gust.start)) / gust.length) ** 2 * gust.power : 0;
      return { speed: 9 + 10 * Math.sin(t * 0.11) + 6 * Math.sin(t * 0.27 + 1.3) + g, gust: g };
    }
    window.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse") return;
      const now = performance.now();
      const dt = Math.max(8, now - mouse.at);
      if (now - mouse.at < 120) {
        mouse.vx = Math.max(-2500, Math.min(2500, ((event.clientX - mouse.x) / dt) * 1000));
        mouse.vy = Math.max(-2500, Math.min(2500, ((event.clientY - mouse.y) / dt) * 1000));
      }
      mouse.x = event.clientX;
      mouse.y = event.clientY;
      mouse.at = now;
    }, { passive: true });

    function tick(time) {
      frame = 0;
      const dt = last ? Math.min(0.05, (time - last) / 1000) : 0;
      last = time;
      clock += dt;
      const air = wind(clock);
      const scrolled = window.scrollY - scroll;
      scroll = window.scrollY;
      const stirred = time - mouse.at < 90;
      const reach = 150;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, petalCanvas.width, petalCanvas.height);
      for (const p of petals) {
        if (stirred) {
          const dx = p.x - mouse.x, dy = p.y - mouse.y;
          const d = Math.hypot(dx, dy);
          if (d < reach) {
            const f = (1 - d / reach) ** 2 * Math.min(1, dt * 10);
            p.vx += (mouse.vx * 0.45 - p.vx) * f;
            p.vy += (mouse.vy * 0.3 - p.vy) * f;
            p.spin += (mouse.vx / 600) * f;
          }
        }
        p.vx *= Math.exp(-dt * 1.3);
        p.vy *= Math.exp(-dt * 1.6);
        if (Math.abs(p.spin) > 0.8) p.spin *= Math.exp(-dt * 0.6); // a swat spins it fast, then it calms down
        p.phase += dt;
        p.flip += p.flipSpeed * dt * (1 + air.gust / 40);
        p.angle += p.spin * dt;
        const sx = Math.cos(p.flip);
        const edge = 1 - Math.abs(sx);
        p.x += (air.speed * (0.55 + 0.45 * p.z) + Math.sin(p.phase) * p.drift + p.vx) * dt;
        p.y += (p.fall * p.z * (0.8 + 0.45 * edge) + p.vy) * dt - scrolled * 0.18 * p.z; // edge-on falls faster
        if (p.y > height + 40) spawn(p, false);
        else if (p.y < -90) p.y = height + 30;
        if (p.x > width + 50) { p.x = -40; p.y = Math.random() * height * 0.8; }
        else if (p.x < -60) p.x = width + 40;

        const image = sprites[p.tone][sx < 0 ? 1 : 0][p.soft ? 1 : 0];
        const k = (p.size / SPRITE) * ratio;
        const fx = (Math.abs(sx) < 0.1 ? 0.1 : Math.abs(sx)) * k;
        const fy = (0.82 + 0.18 * Math.sin(p.flip * 0.6 + p.phase)) * k;
        const cos = Math.cos(p.angle), sin = Math.sin(p.angle);
        ctx.setTransform(cos * fx, sin * fx, -sin * fy, cos * fy, p.x * ratio, p.y * ratio);
        ctx.globalAlpha = p.alpha * tint;
        ctx.drawImage(image.canvas, -image.x, -image.y);
      }
      ctx.globalAlpha = 1;
      if (!document.hidden && !still.matches) frame = requestAnimationFrame(tick);
    }
    const start = () => {
      if (still.matches) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, petalCanvas.width, petalCanvas.height);
        return;
      }
      if (!frame && !document.hidden) { last = 0; scroll = window.scrollY; frame = requestAnimationFrame(tick); }
    };
    paint();
    document.addEventListener("themechange", paint);
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
