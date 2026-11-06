export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const error = new Error(
      data?.error?.message ?? "网络请求失败，请稍后重试",
    ) as Error & { status: number; trace?: string };
    error.status = response.status;
    error.trace = data?.error?.trace_id;
    throw error;
  }
  return response.json();
}

export const post = (body?: unknown): RequestInit => ({
  method: "POST",
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
});

export type Fact = {
  id: string;
  claim: string;
  source: string;
  verified: boolean;
};
export type Brand = {
  id: string;
  name: string;
  description: string;
  audience: string;
  website: string;
  facts: Fact[];
  revision: number;
};
export type Creator = {
  id: string;
  brand_id: string;
  name: string;
  status: string;
  timezone: string;
  hour: number;
  style: string;
  platform: string;
  weekdays: number[];
  daily_budget_cents: number;
  monthly_budget_cents: number;
  model_consent: boolean;
  next_run_at: string | null;
  active_strategy_id: string | null;
};
export type EditorialEntry = {
  id: string;
  creator_id: string;
  date: string;
  title: string;
  angle: string;
  fact_refs: string[];
  fact_evidence: Fact[];
  available_facts: Fact[];
  facts_stale: boolean;
  brand_revision: number;
  revision: number;
  locked: boolean;
  source: string;
  rationale: string;
  status: string;
  due_at: string;
  run_id: string | null;
};
export type Content = {
  id: string;
  creator_id: string;
  run_id: string;
  title: string;
  body: string;
  status: string;
  platform: string;
  generation_source: string;
  revision: number;
  approved_revision: number | null;
  video_attachment: {
    video_id: string;
    revision: number;
    sha256: string;
  } | null;
  created_at: string;
  compliance: { status: string; issues: { level: string; message: string }[] };
  fact_refs: string[];
  variants: Record<
    string,
    { title: string; body: string; tags: string[] }
  > | null;
  graphics: GraphicDocument | null;
  graphics_render: GraphicReceipt | null;
};
export type GraphicPage = {
  page_id: string;
  template: "editorial" | "checklist" | "screenshot";
  heading: string;
  text: string;
  asset_id: string | null;
};
export type GraphicDocument = {
  schema_version: "1.0";
  renderer_version: "graphic_cards@1";
  size: "portrait" | "square" | "landscape";
  theme: "midnight" | "paper" | "sage";
  pages: GraphicPage[];
};
export type GraphicReceipt = {
  content_revision: number;
  cache_key: string;
  renderer_version: string;
  font: { name: string[]; sha256: string };
  pages: {
    page_id: string;
    heading: string;
    width: number;
    height: number;
    png_sha256: string;
    jpg_sha256: string;
  }[];
};
export type Run = {
  id: string;
  status: string;
  stage: string;
  operational_date: string;
  trace_id: string;
  error_code: string | null;
  release: Record<string, unknown>;
  input_snapshot: {
    entry_id: string;
    revision: number;
    title: string;
    angle: string;
  } | null;
};
export type Asset = {
  id: string;
  brand_id: string;
  name: string;
  kind: string;
  verified: boolean;
  source: string;
  license_note: string;
  sha256: string;
};
export type Shot = {
  shot_id: string;
  shot_revision: number;
  provider: string;
  kind: string;
  duration_frames: number;
  caption: string;
  asset_id: string | null;
  locked: boolean;
  trim_start_frame?: number;
  speed_percent?: number;
};
export type AudioTrack = {
  track_id: string;
  asset_id: string;
  role: "voiceover" | "music";
  start_frame: number;
  duration_frames: number;
  source_start_frame: number;
  volume_percent: number;
  loop: boolean;
};
export type Subtitle = {
  cue_id: string;
  start_frame: number;
  end_frame: number;
  text: string;
};
export type Video = {
  id: string;
  brand_id: string;
  name: string;
  status: string;
  revision: number;
  rendered_revision: number | null;
  ir: {
    schema_version?: string;
    brand_id: string;
    name: string;
    width: number;
    height: number;
    fps: number;
    shots: Shot[];
    audio_tracks?: AudioTrack[];
    subtitles?: Subtitle[];
  };
};
export type Handoff = {
  id: string;
  content_id: string;
  content_revision: number;
  platform: string;
  snapshot: { title: string; body: string };
};
export type Publication = {
  id: string;
  package_id: string;
  published_at: string;
  source: string;
  url: string;
  notes: string;
};
export type Metric = {
  id: string;
  content_id: string;
  values: Record<string, number | null>;
  observed_at: string;
  data_source: string;
};
export type Analytics = {
  snapshot_count: number;
  conclusion: string;
  groups: {
    platform: string;
    period_start: string;
    period_end: string;
    data_source: string;
    snapshots: Metric[];
  }[];
};
export type Dashboard = {
  counts: {
    contents: number;
    awaiting_review: number;
    awaiting_manual: number;
    user_reported: number;
  };
  spent_cents: number;
  generation_mode: string;
};
export type Store = {
  brands: Brand[];
  creators: Creator[];
  contents: Content[];
  runs: Run[];
  assets: Asset[];
  videos: Video[];
  handoffs: Handoff[];
  publications: Publication[];
  analytics: Analytics;
  dashboard: Dashboard;
  user: { name: string; email: string; role: string };
};
