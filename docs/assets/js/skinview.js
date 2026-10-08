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
