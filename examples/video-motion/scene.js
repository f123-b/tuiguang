import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const W = 1920,
  H = 1080,
  D = 30,
  FPS = 30;
const output = document.querySelector("#output"),
  ctx = output.getContext("2d");
const status = document.querySelector("#status");
const render = new T.WebGLRenderer({
  antialias: true,
  preserveDrawingBuffer: true,
  powerPreference: "high-performance",
});
render.setSize(W, H);
render.setPixelRatio(1);
render.shadowMap.enabled = true;
render.shadowMap.type = T.PCFSoftShadowMap;
render.toneMapping = T.ACESFilmicToneMapping;
render.toneMappingExposure = 0.95;
const scene = new T.Scene();
scene.background = new T.Color("#e6e7e2");
scene.fog = new T.Fog("#e6e7e2", 24, 65);
const camera = new T.PerspectiveCamera(39, W / H, 0.1, 110);
const environment = new T.PMREMGenerator(render).fromScene(
  new RoomEnvironment(),
  0.04,
);
scene.environment = environment.texture;
scene.environmentIntensity = 0.45;
scene.add(new T.HemisphereLight("#ffffff", "#9cabb4", 1.2));
const key = new T.DirectionalLight("#fff6e3", 2.6);
key.position.set(-5, 11, 8);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, {
  left: -16,
  right: 16,
  top: 16,
  bottom: -16,
  near: 1,
  far: 50,
});
key.shadow.normalBias = 0.025;
key.shadow.radius = 5;
scene.add(key);
const fill = new T.DirectionalLight("#b9d0ff", 1.2);
fill.position.set(8, 5, -3);
scene.add(fill);
const floor = new T.Mesh(
  new T.PlaneGeometry(160, 160),
  new T.MeshStandardMaterial({
    color: "#e2e4df",
    roughness: 0.65,
    metalness: 0.07,
  }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.12;
floor.receiveShadow = true;
scene.add(floor);
const composer = new EffectComposer(render);
composer.addPass(new RenderPass(scene, camera));
const bokeh = new BokehPass(scene, camera, {
  focus: 10,
  aperture: 0.00004,
  maxblur: 0.005,
});
composer.addPass(bokeh);
composer.addPass(new OutputPass());
const clamp = (x) => Math.max(0, Math.min(1, x)),
  smooth = (x) => {
    x = clamp(x);
    return x * x * x * (10 - 15 * x + 6 * x * x);
  };
const lerp = T.MathUtils.lerp;
function texture(draw, w = 1400, h = 1000) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const d = c.getContext("2d");
  draw(d, w, h);
  const tex = new T.CanvasTexture(c);
  tex.colorSpace = T.SRGBColorSpace;
  tex.anisotropy = Math.min(8, render.capabilities.getMaxAnisotropy());
  return tex;
}
function noteTexture(i) {
  return texture((d, w, h) => {
    d.fillStyle = "#f9f8f1";
    d.fillRect(0, 0, w, h);
    d.fillStyle = "#47695f";
    d.font = '500 27px "Microsoft YaHei"';
    d.fillText("示例经历 / " + String(i + 1).padStart(2, "0"), 90, 100);
    d.fillStyle = "#142c27";
    d.font = '600 78px "Microsoft YaHei"';
    d.fillText(["我负责的那一块", "为什么这样选", "怎么验证"][i], 90, 310);
    d.fillStyle = "#5a7069";
    d.font = '36px "Microsoft YaHei"';
    d.fillText(
      [
        "文档列表、筛选与详情",
        "让选择在返回时保留",
        "搜索 · 空数据 · 失败状态",
      ][i],
      90,
      405,
    );
    d.strokeStyle = "#d5ded6";
    d.lineWidth = 2;
    for (let y = 540; y < 830; y += 90) {
      d.beginPath();
      d.moveTo(90, y);
      d.lineTo(1260 - (y % 3) * 55, y);
      d.stroke();
    }
    d.fillStyle = "#3a5fea";
    d.fillRect(90, 875, 95, 7);
  });
}
const notes = [];
for (let i = 0; i < 3; i++) {
  const geo = new T.PlaneGeometry(5, 3.57, 64, 32),
    p = geo.attributes.position;
  for (let n = 0; n < p.count; n++) {
    const x = p.getX(n),
      y = p.getY(n);
    p.setZ(n, 0.065 * x * x + 0.07 * Math.sin(x * 1.3 + y * 0.4));
  }
  geo.computeVertexNormals();
  const material = new T.MeshPhysicalMaterial({
    map: noteTexture(i),
    roughness: 0.82,
    metalness: 0,
    side: T.DoubleSide,
    clearcoat: 0.15,
  });
  const mesh = new T.Mesh(geo, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  notes.push(mesh);
}
// Brushed, gently bevelled frame around an actual captured application image.
const app = new T.Group();
scene.add(app);
const chassis = new T.Mesh(
  new RoundedBoxGeometry(11.68, 7.46, 0.18, 6, 0.13),
  new T.MeshPhysicalMaterial({
    color: "#bec7c7",
    metalness: 0.85,
    roughness: 0.23,
    clearcoat: 0.7,
    clearcoatRoughness: 0.25,
  }),
);
chassis.castShadow = true;
app.add(chassis);
const black = new T.Mesh(
  new RoundedBoxGeometry(11.45, 7.22, 0.09, 4, 0.09),
  new T.MeshStandardMaterial({
    color: "#182727",
    roughness: 0.36,
    metalness: 0.2,
  }),
);
black.position.z = 0.105;
app.add(black);
const uiCanvas = document.createElement("canvas");
uiCanvas.width = 2048;
uiCanvas.height = 1280;
const ud = uiCanvas.getContext("2d");
const uiTex = new T.CanvasTexture(uiCanvas);
uiTex.colorSpace = T.SRGBColorSpace;
uiTex.anisotropy = 8;
const screen = new T.Mesh(
  new T.PlaneGeometry(11.2, 7),
  new T.MeshBasicMaterial({ map: uiTex, toneMapped: false }),
);
screen.position.z = 0.164;
app.add(screen);
const capture = await (await fetch("/assets/capture.json")).json();
const uiFrames = await Promise.all(
  capture.frames.map(
    (f) =>
      new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve({ ...f, image });
        image.onerror = reject;
        image.src = f.url;
      }),
  ),
);
let uiIndex = -1;
function updateUI(time) {
  let index = 0;
  for (let i = 0; i < uiFrames.length; i++) {
    if (uiFrames[i].wall <= time) index = i;
    else break;
  }
  if (index !== uiIndex) {
    ud.drawImage(uiFrames[index].image, 0, 0, 2048, 1280);
    uiTex.needsUpdate = true;
    uiIndex = index;
  }
}
updateUI(0);
// A flattened, twisting ribbon connects the objects in real 3-D space.
const path = new T.CatmullRomCurve3(
  [
    new T.Vector3(-9, 0.2, 2),
    new T.Vector3(-6, 1.3, 1),
    new T.Vector3(-3, 4.9, -1),
    new T.Vector3(-1, 1.6, -1.6),
    new T.Vector3(1.6, 5, -2),
    new T.Vector3(3.2, 4.8, -2.8),
    new T.Vector3(6, 3.6, -3),
    new T.Vector3(6.8, 1.7, 1.7),
    new T.Vector3(4.2, 0.5, 3.5),
    new T.Vector3(-1, 0.15, 4.7),
    new T.Vector3(-6, 0.6, 1.5),
  ],
  false,
  "catmullrom",
  0.35,
);
const N = 420,
  pts = [],
  uv = [],
  idx = [],
  basis = path.computeFrenetFrames(N, false);
for (let i = 0; i <= N; i++) {
  const s = i / N,
    c = path.getPointAt(s);
  const across = basis.normals[i]
    .clone()
    .multiplyScalar(Math.cos(s * 13))
    .addScaledVector(basis.binormals[i], Math.sin(s * 13));
  for (const side of [-1, 1]) {
    const q = c.clone().addScaledVector(across, 0.14 * side);
    pts.push(q.x, q.y, q.z);
    uv.push(s, side === 1 ? 1 : 0);
  }
  if (i < N) {
    let n = i * 2;
    idx.push(n, n + 1, n + 2, n + 1, n + 3, n + 2);
  }
}
const ribbonGeo = new T.BufferGeometry();
ribbonGeo.setAttribute("position", new T.Float32BufferAttribute(pts, 3));
ribbonGeo.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
ribbonGeo.setIndex(idx);
ribbonGeo.computeVertexNormals();
const ribbon = new T.Mesh(
  ribbonGeo,
  new T.MeshPhysicalMaterial({
    color: "#2449df",
    metalness: 0.68,
    roughness: 0.21,
    clearcoat: 1,
    clearcoatRoughness: 0.1,
    side: T.DoubleSide,
  }),
);
ribbon.castShadow = true;
ribbon.receiveShadow = true;
scene.add(ribbon);
const tip = new T.Mesh(
  new T.SphereGeometry(0.15, 28, 16),
  new T.MeshPhysicalMaterial({
    color: "#b6c8ff",
    metalness: 1,
    roughness: 0.13,
  }),
);
scene.add(tip);
function overlay(t) {
  ctx.font = '500 25px "Microsoft YaHei"';
  ctx.fillStyle = "rgba(18,45,39,.65)";
  ctx.fillText("有招 / YOUZHAO", 76, 70);
  ctx.textAlign = "right";
  ctx.font = '21px "Microsoft YaHei"';
  ctx.fillText(
    t < 13 ? "情景示意 · 合成配音" : "真实界面 · 演示资料",
    W - 76,
    70,
  );
  ctx.textAlign = "left";
  const captions = [
    ["做过的项目，", 0, 4.8],
    ["怎么讲成自己的故事？", 1.35, 4.8],
    ["找到你负责的那一块。", 5.5, 11],
    ["让经历，有自己的逻辑。", 11.4, 15.5],
    ["", 17.2, 23],
    ["把你做过的，讲清楚。", 25, 30],
  ];
  for (let i = 0; i < captions.length; i++) {
    const [words, start, end] = captions[i];
    if (t < start || t > end) continue;
    const a = smooth((t - start) / 0.65) * (1 - smooth((t - end + 0.5) / 0.5));
    ctx.globalAlpha = a;
    ctx.font = `500 ${i === 5 ? 82 : 67}px "Microsoft YaHei"`;
    ctx.fillStyle = "#15372e";
    let y = i === 0 ? 220 : i === 1 ? 318 : 945;
    ctx.fillText(words, 90, y + 18 * (1 - smooth((t - start) / 0.75)));
    ctx.globalAlpha = 1;
  }
}
function setFrame(t) {
  const gather = smooth((t - 3) / 7),
    reveal = smooth((t - 11) / 4),
    close = smooth((t - 17) / 5),
    end = smooth((t - 24) / 5);
  notes.forEach((mesh, i) => {
    const old = [
        [-6.4, 2.4, 1.5],
        [0, 1.1, -0.4],
        [6.4, 2.5, -1.8],
      ][i],
      target = [
        [-6, 3, 0],
        [0, 3.6, -0.8],
        [6, 2.8, -1],
      ][i];
    mesh.position.set(
      lerp(old[0], target[0], gather),
      lerp(old[1], target[1], gather) +
        Math.sin(t * 0.7 + i) * 0.06 -
        reveal * 5.8,
      lerp(old[2], target[2], gather),
    );
    mesh.rotation.set(
      lerp(-0.4 + i * 0.28, 0.03, gather),
      lerp(-0.3 + i * 0.28, -0.09, gather),
      lerp(0.18 - i * 0.2, -0.03 + i * 0.026, gather),
    );
  });
  app.position.set(0, -5.5 + reveal * 9.5, 0);
  app.rotation.set(-0.04, -0.18 + close * 0.13, 0.02);
  app.scale.setScalar(1);
  const progress = clamp((t - 2) / 15);
  ribbonGeo.setDrawRange(0, Math.max(0, Math.floor(progress * N)) * 6);
  const pt = path.getPointAt(progress);
  tip.position.copy(pt);
  tip.position.y -= reveal * 1.4;
  tip.visible = progress > 0 && progress < 1;
  ribbon.position.y = -reveal * 1.4;
  ribbon.rotation.y = end * 0.4;
  const track = smooth(t / 10);
  const initial = new T.Vector3(
    -6.8 + track * 8.5,
    4.5 + gather * 0.7,
    7 + gather * 9,
  );
  const wide = new T.Vector3(2.5, 5.2, 15.7),
    near = new T.Vector3(3.5, 4.9, 6.8),
    last = new T.Vector3(1.8, 5.8, 17);
  camera.position
    .copy(initial)
    .lerp(wide, reveal)
    .lerp(near, close)
    .lerp(last, end);
  const aim = new T.Vector3(-6 + track * 8.5, 2.6, 0);
  aim
    .lerp(new T.Vector3(0, 4, 0), reveal)
    .lerp(new T.Vector3(3.2, 4.8, 0.2), close)
    .lerp(new T.Vector3(0, 3.8, 0), end);
  camera.lookAt(aim);
  bokeh.uniforms.focus.value = camera.position.distanceTo(aim);
  bokeh.uniforms.aperture.value = lerp(0.00004, 0.000009, reveal);
  updateUI(clamp((t - 15) / 8) * 5.25);
  composer.render();
  ctx.drawImage(render.domElement, 0, 0);
  overlay(t);
  document.querySelector("#scrub").value = t;
}
let running = false,
  exporting = false,
  start = 0;
function animate(now) {
  if (running && !exporting) {
    let t = ((now - start) / 1000) % D;
    setFrame(t);
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
document.querySelector("#play").onclick = () => {
  running = !running;
  start =
    performance.now() - Number(document.querySelector("#scrub").value) * 1000;
};
document.querySelector("#scrub").oninput = (e) => {
  running = false;
  setFrame(Number(e.target.value));
};
async function exportMovie() {
  if (exporting) return;
  exporting = true;
  running = false;
  const headers = {
    "X-Render-Token": document.querySelector('meta[name="render-token"]')
      .content,
  };
  await fetch("/reset", { method: "POST", headers });
  try {
    for (let n = 0; n < D * FPS; n++) {
      setFrame(n / FPS);
      const blob = await new Promise((resolve) =>
        output.toBlob(resolve, "image/png"),
      );
      const r = await fetch("/frame?index=" + n, {
        method: "POST",
        headers,
        body: blob,
      });
      if (!r.ok) throw Error("frame rejected");
      if (n % 15 === 0) {
        status.textContent = `导出 ${n}/${D * FPS}`;
        await new Promise(requestAnimationFrame);
      }
    }
    status.textContent = "导出完成";
  } catch (e) {
    status.textContent = e.message;
    throw e;
  } finally {
    exporting = false;
  }
}
document.querySelector("#export").onclick = exportMovie;
window.motionLab = {
  setFrame,
  exportMovie,
  renderer: render,
  ready: true,
  duration: D,
};
setFrame(5);
status.textContent = "已就绪";
