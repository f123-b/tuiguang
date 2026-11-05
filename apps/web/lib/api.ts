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
};
export type Content = {
  id: string;
  title: string;
  body: string;
  status: string;
  platform: string;
  generation_source: string;
  revision: number;
  approved_revision: number | null;
  created_at: string;
  compliance: { status: string; issues: { level: string; message: string }[] };
  fact_refs: string[];
};
export type Run = {
  id: string;
  status: string;
  stage: string;
  operational_date: string;
  trace_id: string;
  error_code: string | null;
  release: Record<string, unknown>;
};
export type Asset = {
  id: string;
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
};
export type Video = {
  id: string;
  name: string;
  status: string;
  revision: number;
  rendered_revision: number | null;
  ir: { width: number; height: number; fps: number; shots: Shot[] };
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
