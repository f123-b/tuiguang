"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import { useEffect, useState } from "react";
import { api, post, type Asset } from "../../lib/api";
import { Field, type PageProps } from "../page-shared";

type Source = {
  id: string;
  name: string;
  kind: string;
  url: string | null;
  enabled: boolean;
  revision: number;
  current_version: string | null;
  last_checked_at: string | null;
  last_error_code: string | null;
};
type Snapshot = {
  id: string;
  version: string | null;
  sha256: string;
  text: string;
  created_at: string;
};
type Event = {
  id: string;
  snapshot_id: string;
  status: string;
  diff: string;
  proposal_id: string | null;
};
type Check = {
  id: string;
  status: string;
  error_code: string | null;
  created_at: string;
  result: unknown;
};
type Actions = Pick<PageProps, "action" | "busy">;

export function ProductSources({
  brandId,
  action,
  busy,
}: Actions & { brandId: string }) {
  const [sources, setSources] = useState<Source[]>([]),
    [selected, setSelected] = useState(""),
    [snapshots, setSnapshots] = useState<Snapshot[]>([]),
    [events, setEvents] = useState<Event[]>([]),
    [checks, setChecks] = useState<Check[]>([]);
  const [kind, setKind] = useState("github_releases"),
    [refresh, setRefresh] = useState(0),
    [error, setError] = useState("");
  useEffect(() => {
    api<Source[]>(`/brands/${brandId}/product-sources`)
      .then(setSources)
      .catch((e) => setError(e.message));
  }, [brandId, refresh]);
  useEffect(() => {
    if (!selected) return;
    Promise.all([
      api<Snapshot[]>(`/product-sources/${selected}/snapshots`),
      api<Event[]>(`/product-sources/${selected}/events`),
      api<Check[]>(`/product-sources/${selected}/checks`),
    ])
      .then(([s, e, c]) => {
        setSnapshots(s);
        setEvents(e);
        setChecks(c);
      })
      .catch((e) => setError(e.message));
  }, [selected, refresh]);
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      setRefresh((v) => v + 1);
    }, message);
  return (
    <Card>
      <h2>产品动态监测</h2>
      <p>
        仅检查你主动授权的公开来源或上传说明。首次保存基线，以后记录差异；发现变化只进入待核实区，不会自动宣称功能已上线。
      </p>
      {error && <p role="alert">{error}</p>}
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          run(
            () =>
              api(
                `/brands/${brandId}/product-sources`,
                post({
                  name: f.get("name"),
                  kind,
                  url: kind === "uploaded_notes" ? null : f.get("url"),
                  authorized: true,
                  interval_minutes: Number(f.get("interval")),
                }),
              ),
            "来源已保存，后台仅按你授权的设置检查",
          );
        }}
      >
        <div className="form-grid">
          <Field label="来源名称">
            <input name="name" required maxLength={120} />
          </Field>
          <Field label="来源类型">
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="github_releases">公开 GitHub Release</option>
              <option value="url_text">公开文档 / 更新日志</option>
              <option value="uploaded_notes">手工上传版本说明</option>
            </select>
          </Field>
        </div>
        {kind !== "uploaded_notes" && (
          <Field
            label={kind === "github_releases" ? "仓库 URL" : "公开文档 URL"}
          >
            <input
              name="url"
              type="url"
              placeholder={
                kind === "github_releases"
                  ? "https://github.com/所有者/仓库"
                  : "https://example.org/changelog.md"
              }
              required
              maxLength={1000}
            />
          </Field>
        )}
        <Field label="检查间隔（分钟；上传来源仅手工更新）">
          <input
            name="interval"
            type="number"
            min={15}
            max={10080}
            defaultValue={120}
            required
          />
        </Field>
        <label className="checkline">
          <input type="checkbox" required />
          我有权使用此资料，并授权本软件保存快照、定期检查该公开来源。
        </label>
        <Button type="submit" disabled={busy}>
          添加授权来源
        </Button>
      </form>
      {sources.map((s) => (
        <section key={s.id} className="subtle-note">
          <div className="section-heading">
            <h3>{s.name}</h3>
            <Badge tone={s.enabled ? "blue" : "neutral"}>
              {s.enabled ? "已启用" : "已停用"}
            </Badge>
          </div>
          <p>
            当前版本：{s.current_version || "未知或尚无基线"} · 最近检查：
            {s.last_checked_at || "尚未检查"}
          </p>
          {s.last_error_code && (
            <p role="alert">
              检查未完成：{s.last_error_code}，保留上次成功快照。
            </p>
          )}
          {s.url && (
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-link"
            >
              打开公开来源
            </a>
          )}
          <div className="form-actions">
            {s.kind !== "uploaded_notes" && (
              <Button
                disabled={busy || !s.enabled}
                variant="secondary"
                onClick={() =>
                  run(
                    () =>
                      api(
                        `/product-sources/${s.id}/check`,
                        post({ confirmed: true }),
                      ),
                    "来源检查完成，请查看快照和差异",
                  )
                }
              >
                立即检查来源
              </Button>
            )}
            <Button
              disabled={busy}
              variant="quiet"
              onClick={() =>
                run(
                  () =>
                    api(`/product-sources/${s.id}`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        expected_revision: s.revision,
                        enabled: !s.enabled,
                        confirmed: true,
                      }),
                    }),
                  s.enabled ? "来源已停用，不再检查" : "来源已恢复",
                )
              }
            >
              {s.enabled ? "停用监测" : "恢复监测"}
            </Button>
            <Button
              variant="quiet"
              onClick={() => {
                setSelected(s.id);
                setRefresh((v) => v + 1);
              }}
            >
              查看快照与变更
            </Button>
          </div>
          {s.kind === "uploaded_notes" && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                f.set("confirmed", "true");
                run(
                  () =>
                    api(`/product-sources/${s.id}/upload`, {
                      method: "POST",
                      body: f,
                    }),
                  "版本说明已保存；变化尚未成为已核实事实",
                );
              }}
            >
              <Field label="产品版本">
                <input name="version" maxLength={100} required />
              </Field>
              <Field label="UTF-8 版本说明（TXT / MD，最多 512 KiB）">
                <input name="file" type="file" accept=".txt,.md" required />
              </Field>
              <label className="checkline">
                <input type="checkbox" required />
                确认将这份说明作为所填版本的来源记录
              </label>
              <Button type="submit" disabled={busy || !s.enabled}>
                上传这版说明
              </Button>
            </form>
          )}
        </section>
      ))}
      {selected && (
        <section>
          <h3>{sources.find((s) => s.id === selected)?.name} · 证据记录</h3>
          {events.length === 0 && <p>尚未发现与基线不同的内容。</p>}
          {events.map((event) => (
            <details key={event.id}>
              <summary>
                发现来源变化 ·{" "}
                {event.proposal_id ? "已创建待核实提案" : "待人工检查"}
              </summary>
              <pre className="diagnostic-json">{event.diff}</pre>
              {!event.proposal_id && (
                <form
                  className="form-stack"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    run(
                      () =>
                        api(
                          `/product-sources/${selected}/events/${event.id}/propose`,
                          post({
                            claim: f.get("claim"),
                            product_version: f.get("version"),
                            confirmed: true,
                          }),
                        ),
                      "已创建待核实提案，请在品牌变更区核对是否已上线",
                    );
                  }}
                >
                  <Field label="从变化中摘录的功能声明">
                    <textarea name="claim" maxLength={1000} required />
                  </Field>
                  <Field label="声明适用版本">
                    <input
                      name="version"
                      maxLength={100}
                      defaultValue={
                        snapshots.find((s) => s.id === event.snapshot_id)
                          ?.version || ""
                      }
                      required
                    />
                  </Field>
                  <label className="checkline">
                    <input type="checkbox" required />
                    我已查看来源，先创建待核实提案，稍后另行审批是否已上线
                  </label>
                  <Button type="submit" disabled={busy}>
                    创建待核实提案
                  </Button>
                </form>
              )}
            </details>
          ))}
          <details>
            <summary>不可变来源快照（最近 30 份）</summary>
            {snapshots.map((s) => (
              <section key={s.id}>
                <h4>
                  {s.version || "版本未知"} · {s.created_at}
                </h4>
                <p className="muted">证据哈希 {s.sha256}</p>
                <pre className="diagnostic-json">{s.text}</pre>
              </section>
            ))}
          </details>
          <details>
            <summary>检查回执</summary>
            <pre className="diagnostic-json">
              {JSON.stringify(checks, null, 2)}
            </pre>
          </details>
        </section>
      )}
    </Card>
  );
}

export function AssetVersions({
  brandId,
  assets,
  action,
  busy,
}: Actions & { brandId?: string; assets: Asset[] }) {
  const [sources, setSources] = useState<Source[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    if (brandId)
      api<Source[]>(`/brands/${brandId}/product-sources`)
        .then(setSources)
        .catch((e) => setError(e.message));
  }, [brandId]);
  if (!assets.length) return null;
  return (
    <Card>
      <h2>素材适用产品版本</h2>
      <p>
        把截图、录屏与某个产品来源关联。来源变化会暂停使用这份素材并要求复核；确认适用版本后，还须单独核实素材使用权。
      </p>
      {error && <p role="alert">{error}</p>}
      {assets.map((a) => (
        <form
          key={`${a.id}-${a.product_version}-${a.applicability_status}`}
          className="form-stack subtle-note"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            action(
              () =>
                api(`/assets/${a.id}/applicability`, {
                  method: "PUT",
                  body: JSON.stringify({
                    source_id: String(f.get("source") || "") || null,
                    product_version: String(f.get("version") || "") || null,
                    confirmed: true,
                  }),
                }),
              "适用版本已记录，请继续核实素材授权",
            );
          }}
        >
          <h3>{a.name}</h3>
          {a.applicability_status === "needs_review" && (
            <Badge tone="warning">来源变化，素材版本待复核</Badge>
          )}
          <div className="form-grid">
            <Field label="关联产品来源">
              <select name="source" defaultValue={a.product_source_id || ""}>
                <option value="">不关联来源</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} · {s.current_version || "版本未知"}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="已核对适用版本">
              <input
                name="version"
                maxLength={100}
                defaultValue={a.product_version || ""}
              />
            </Field>
          </div>
          <label className="checkline">
            <input type="checkbox" required />
            我已对照当前来源核实该素材的适用版本
          </label>
          <Button type="submit" variant="secondary" disabled={busy}>
            保存适用版本
          </Button>
        </form>
      ))}
    </Card>
  );
}
