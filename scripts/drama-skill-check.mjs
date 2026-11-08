// Fixed offline adapter. No caller supplied code, paths, commands or network.
import {
  gateReport,
  computeStats,
} from "../vendor/skills/shuohao/novel-script/scripts/novel-script.mjs";
let text = "";
for await (const chunk of process.stdin) {
  text += chunk;
  if (Buffer.byteLength(text) > 180000) throw new Error("input limit");
}
const { plan, target } = JSON.parse(text);
const scenes = plan.shots.map((s) => ({
  sceneId: s.scene_id,
  characters: s.character_ids,
  flow: [
    { action: s.action },
    ...(s.narration
      ? [{ speaker: "VO", line: s.narration, delivery: s.delivery }]
      : []),
  ],
}));
// Action and spoken beats are a conservative sequential estimate, separate from
// the final measured TTS duration. Never claim generated performance or lip sync.
const doc = {
  source: plan.title,
  params: { actionSeconds: 2.5 },
  episodes: [
    {
      ep: 1,
      targetSeconds: target,
      hook: plan.hook,
      cliff: plan.beats.at(-1).result,
      hookBeat: [1, 1],
      beatsClaimed: plan.beats.map((b) => b.id),
      scenes,
    },
  ],
};
const gates = gateReport(doc, {
  outline: { characters: plan.characters, beats: [] },
  art: { scenes: plan.scenes.map((s) => ({ id: s.id })), props: [] },
});
process.stdout.write(
  JSON.stringify({
    validator: "shuohao/novel-script",
    gates,
    errors: gates
      .filter((g) => !g.ok)
      .map((g) => ({ code: g.id, message: g.label, detail: g.detail })),
    stats: computeStats(doc),
  }),
);
