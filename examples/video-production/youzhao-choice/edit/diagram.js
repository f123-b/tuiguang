import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const W = 1920,
  H = 1080,
  FPS = 30,
  D = 6;
const canvas = document.querySelector("#film"),
  ctx = canvas.getContext("2d");
const renderer = new T.WebGLRenderer({
  antialias: true,
  preserveDrawingBuffer: true,
  powerPreference: "high-performance",
});
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.toneMapping = T.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
const scene = new T.Scene();
scene.background = new T.Color("#c4b5a1");
scene.environment = new T.PMREMGenerator(renderer).fromScene(
  new RoomEnvironment(),
  0.04,
).texture;
scene.environmentIntensity = 0.25;
scene.add(new T.HemisphereLight("#fff6e9", "#594e43", 1.4));
const key = new T.DirectionalLight("#ffe2b1", 3.1);
key.position.set(-8, 13, 6);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, {
  left: -13,
  right: 13,
  top: 12,
  bottom: -12,
  near: 1,
  far: 40,
});
key.shadow.normalBias = 0.02;
key.shadow.radius = 4;
scene.add(key);
const fill = new T.DirectionalLight("#c0d9df", 0.7);
fill.position.set(10, 6, -8);
scene.add(fill);
const camera = new T.PerspectiveCamera(40, W / H, 0.1, 100);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bokeh = new BokehPass(scene, camera, {
  focus: 15,
  aperture: 0.000009,
  maxblur: 0.0035,
});
composer.addPass(bokeh);
composer.addPass(new OutputPass());
let seed = 71;
const random = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296;
};
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => {
  x = clamp(x);
  return x * x * x * (10 + x * (-15 + 6 * x));
};
const mix = T.MathUtils.lerp;
function texture(w, h, paint) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  paint(c.getContext("2d"), w, h);
  const t = new T.CanvasTexture(c);
  t.colorSpace = T.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
const wood = texture(2048, 1024, (d, w, h) => {
  d.fillStyle = "#92795e";
  d.fillRect(0, 0, w, h);
  for (let i = 0; i < 1300; i++) {
    const y = random() * h;
    d.strokeStyle = `rgba(${random() < 0.5 ? "50,36,25" : "218,194,153"},${random() * 0.08})`;
    d.lineWidth = 0.5 + random() * 2;
    d.beginPath();
    d.moveTo(0, y);
    d.bezierCurveTo(
      w * 0.3,
      y + random() * 18,
      w * 0.7,
      y - 10,
      w,
      y + random() * 13,
    );
    d.stroke();
  }
});
const desk = new T.Mesh(
  new T.BoxGeometry(80, 0.5, 60),
  new T.MeshStandardMaterial({ map: wood, roughness: 0.73 }),
);
desk.position.y = -0.5;
desk.receiveShadow = true;
scene.add(desk);
const paper = texture(2048, 1400, (d, w, h) => {
  d.fillStyle = "#ece5d6";
  d.fillRect(0, 0, w, h);
  for (let i = 0; i < 38000; i++) {
    d.fillStyle = `rgba(69,54,35,${random() * 0.035})`;
    d.fillRect(random() * w, random() * h, 1 + random(), 1 + random());
  }
  d.strokeStyle = "rgba(94,125,128,.11)";
  d.lineWidth = 1;
  for (let x = 0; x < w; x += 48) {
    d.beginPath();
    d.moveTo(x, 0);
    d.lineTo(x, h);
    d.stroke();
  }
  for (let y = 0; y < h; y += 48) {
    d.beginPath();
    d.moveTo(0, y);
    d.lineTo(w, y);
    d.stroke();
  }
  d.fillStyle = "rgba(76,60,42,.13)";
  d.fillRect(w / 2 - 2, 0, 4, h);
});
for (let i = 0; i < 5; i++) {
  const page = new T.Mesh(
    new RoundedBoxGeometry(18, 0.035, 11.8, 2, 0.02),
    new T.MeshStandardMaterial({ color: "#e7e0d1", roughness: 1 }),
  );
  page.position.set(i * 0.015, -0.13 + i * 0.035, i * 0.015);
  page.receiveShadow = true;
  page.castShadow = true;
  scene.add(page);
}
const sheet = new T.Mesh(
  new T.PlaneGeometry(18, 11.8),
  new T.MeshStandardMaterial({ map: paper, roughness: 1 }),
);
sheet.rotation.x = -Math.PI / 2;
sheet.position.y = 0.035;
sheet.receiveShadow = true;
scene.add(sheet);
function label(
  words,
  size = 82,
  color = "#254b43",
  width = 1000,
  height = 220,
) {
  const map = texture(width, height, (d, w, h) => {
    d.clearRect(0, 0, w, h);
    d.font = `600 ${size}px "Microsoft YaHei"`;
    d.fillStyle = color;
    d.textAlign = "center";
    d.textBaseline = "middle";
    d.fillText(words, w / 2, h / 2);
  });
  const m = new T.Mesh(
    new T.PlaneGeometry(width / 220, height / 220),
    new T.MeshBasicMaterial({
      map,
      transparent: true,
      depthWrite: false,
      toneMapped: false,
    }),
  );
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.065;
  scene.add(m);
  return m;
}
const heading = label("全量 / 分批", 100, "#263e37", 1400, 240);
heading.position.set(0, 0.07, -4.65);
const leftLabel = label("待处理记录", 60, "#6e6e5e", 900, 180);
leftLabel.position.set(-5, 0.07, 3.9);
const rightLabel = label("先看到内容", 60, "#6e6e5e", 900, 180);
rightLabel.position.set(4, 0.07, 3.9);
const pathCurve = new T.CatmullRomCurve3([
  new T.Vector3(-4, 0.09, 0.7),
  new T.Vector3(-1, 0.09, 0.7),
  new T.Vector3(0.2, 0.09, -0.2),
  new T.Vector3(3, 0.09, -0.2),
]);
const guide = new T.Mesh(
  new T.TubeGeometry(pathCurve, 80, 0.025, 7, false),
  new T.MeshStandardMaterial({ color: "#849486", roughness: 0.8 }),
);
scene.add(guide);
const folder = new T.Mesh(
  new RoundedBoxGeometry(5.2, 0.09, 5.9, 2, 0.08),
  new T.MeshStandardMaterial({ color: "#d6d8c6", roughness: 0.95 }),
);
folder.position.set(3.8, 0.08, -0.3);
folder.castShadow = true;
folder.receiveShadow = true;
scene.add(folder);
const cardTex = texture(512, 320, (d, w, h) => {
  d.fillStyle = "#f8f2e8";
  d.fillRect(0, 0, w, h);
  d.fillStyle = "#7e9b90";
  d.fillRect(42, 44, 68, 68);
  d.fillStyle = "#b9b5a9";
  d.fillRect(137, 50, 285, 15);
  d.fillRect(137, 83, 205, 12);
  d.fillStyle = "#d4d0c5";
  for (let i = 0; i < 4; i++) d.fillRect(42, 145 + i * 31, 370 - i * 24, 10);
});
const cardGeometry = new RoundedBoxGeometry(1.56, 0.055, 1.02, 2, 0.035);
const sideMaterial = new T.MeshStandardMaterial({
  color: "#e6dece",
  roughness: 1,
});
const faceMaterial = new T.MeshStandardMaterial({
  map: cardTex,
  roughness: 0.92,
});
const cards = [];
for (let i = 0; i < 48; i++) {
  const group = new T.Group();
  const card = new T.Mesh(cardGeometry, sideMaterial);
  card.castShadow = true;
  card.receiveShadow = true;
  group.add(card);
  const face = new T.Mesh(new T.PlaneGeometry(1.5, 0.96), faceMaterial);
  face.rotation.x = -Math.PI / 2;
  face.position.y = 0.03;
  face.receiveShadow = true;
  group.add(face);
  scene.add(group);
  cards.push(group);
}
// A real pencil-like object at the notebook edge ties the diagram to the live-action material.
const pencil = new T.Group();
const shaft = new T.Mesh(
  new T.CylinderGeometry(0.07, 0.07, 7.5, 6),
  new T.MeshStandardMaterial({ color: "#8c3324", roughness: 0.55 }),
);
pencil.add(shaft);
const tip = new T.Mesh(
  new T.ConeGeometry(0.07, 0.5, 10),
  new T.MeshStandardMaterial({ color: "#aa8a55", roughness: 0.7 }),
);
tip.position.y = 4;
pencil.add(tip);
pencil.rotation.set(Math.PI / 2, 0, -0.17);
pencil.position.set(-1, 0.16, 5.4);
pencil.traverse((o) => {
  if (o.isMesh) o.castShadow = true;
});
scene.add(pencil);

function setFrame(mode, t) {
  const batch = mode === "batch";
  cards.forEach((card, i) => {
    const sx = -5 + (i % 2) * 0.14,
      sz = -0.4 + Math.floor(i / 16) * 0.07,
      sy = 0.2 + i * 0.035;
    let x = sx,
      y = sy,
      z = sz,
      rx = 0,
      ry = 0,
      rz = 0;
    if (!batch) {
      const p = ease((t - 0.15 - i * 0.018) / 1.5);
      const tx = 3.5 + Math.sin(i * 4.7) * 0.46,
        tz = -0.4 + Math.cos(i * 3.1) * 0.5;
      x = mix(sx, tx, p);
      z = mix(sz, tz, p);
      y =
        mix(sy, 0.22 + i * 0.063, p) +
        Math.sin(Math.PI * p) * (1.8 + (i % 5) * 0.15);
      ry = p * ((i % 5) - 2) * 0.11;
      rz = Math.sin(p * Math.PI) * 0.14;
    } else if (i < 6) {
      const p = ease((t - 0.15 - i * 0.22) / 1.3);
      const tx = 2.25 + (i % 2) * 1.65,
        tz = -2.05 + Math.floor(i / 2) * 1.16;
      x = mix(sx, tx, p);
      z = mix(sz, tz, p);
      y = mix(sy, 0.19, p) + Math.sin(Math.PI * p) * 0.9;
      ry = (1 - p) * Math.sin(i) * 0.1;
    } else {
      y = 0.2 + (i - 6) * 0.035;
    }
    card.position.set(x, y, z);
    card.rotation.set(rx, ry, rz);
  });
  const u = ease(t / D);
  camera.position.set(mix(8.1, 6.8, u), mix(13.8, 12.8, u), mix(13.9, 12.1, u));
  const aim = new T.Vector3(batch ? 0.3 : 0.9, 0.5, 0);
  camera.lookAt(aim);
  bokeh.uniforms.focus.value = camera.position.distanceTo(aim);
  composer.render();
  ctx.drawImage(renderer.domElement, 0, 0);
  // Editorial labels are separate from the diagram and never resemble product UI.
  ctx.fillStyle = "#243e35";
  ctx.font = '600 58px "Microsoft YaHei"';
  ctx.fillText(
    batch ? "先到一批，先看一批。" : "一次全给，先等全部。",
    110,
    150,
  );
  ctx.fillStyle = "#626e61";
  ctx.font = '26px "Microsoft YaHei"';
  ctx.fillText("虚构项目 · 方案示意 · 非软件性能测试", 112, 197);
  document.querySelector("#state").textContent = `${mode} ${t.toFixed(2)}s`;
}
async function exportFrames() {
  const headers = {
    "X-Render-Token": document.querySelector('meta[name="render-token"]')
      .content,
  };
  await fetch("/reset", { method: "POST", headers });
  for (const [j, mode] of ["all", "batch"].entries())
    for (let n = 0; n < D * FPS; n++) {
      setFrame(mode, n / FPS);
      const body = await new Promise((r) => canvas.toBlob(r, "image/png"));
      const response = await fetch(`/frame?index=${j * D * FPS + n}`, {
        method: "POST",
        headers,
        body,
      });
      if (!response.ok) throw Error("frame rejected");
      if (n % 10 === 0) await new Promise(requestAnimationFrame);
    }
  document.querySelector("#state").textContent = "360帧导出完成";
  return { frames: 360 };
}
document.querySelector("#render").onclick = exportFrames;
window.choiceDiagram = { setFrame, exportFrames, ready: true, renderer };
setFrame("batch", 3.3);
