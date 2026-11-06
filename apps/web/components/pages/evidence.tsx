"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import { useEffect, useState } from "react";
import { api, post, type Brand, type Content } from "../../lib/api";
import { Field, platformName, type PageProps } from "../page-shared";

type Revision = {
  revision: number;
  reason_tag: string;
  created_at: string;
  snapshot: {
    title: string;
    body: string;
    graphics: unknown;
    variants: unknown;
  };
};
type Change = {
  id: string;
  claim: string;
  source: string;
  product_version: string;
  status: string;
};
type Actions = Pick<PageProps, "action" | "busy">;

export function ContentEvidence({
  content,
  onDraftChange,
  action,
  busy,
  locked,
}: Actions & {
  content: Content;
  locked: boolean;
  onDraftChange: (value: boolean) => void;
}) {
  const [draftDirty, setDraftDirty] = useState(false);
  const [history, setHistory] = useState<Revision[]>([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Revision | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [platform, setPlatform] = useState("douyin");
  useEffect(() => {
    setSelected(null);
    setDraftDirty(false);
    setConfirmed(false);
    api<Revision[]>(`/content/packages/${content.id}/history`)
      .then(setHistory)
      .catch((e) => setError(e.message));
  }, [content.id, content.revision]);
  const variant = content.variants?.[platform];
  return (
    <Card>
      <details>
        <summary>修订历史与平台文案 · 当前 V{content.revision}</summary>
        {error && <p role="alert">{error}</p>}
        <div className="form-columns">
          <section>
            <h3>版本比较与恢复</h3>
            <p className="muted">
              恢复会生成待审核的新版本，不改变历史发布记录。有未保存修改时请先保存。
            </p>
            <div className="form-actions">
              {history.map((h) => (
                <Button
                  key={h.revision}
                  variant="quiet"
                  onClick={() => {
                    setSelected(h);
                    setConfirmed(false);
                  }}
                >
                  V{h.revision} · {h.reason_tag}
                </Button>
              ))}
            </div>
            {selected && (
              <>
                <h4>
                  V{selected.revision} → 当前 V{content.revision}
                </h4>
                <div className="form-columns">
                  <div>
                    <strong>选择的版本</strong>
                    <pre className="diagnostic-json">
                      {JSON.stringify(selected.snapshot, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <strong>当前版本</strong>
                    <pre className="diagnostic-json">
                      {JSON.stringify(
                        {
                          title: content.title,
                          body: content.body,
                          graphics: content.graphics,
                          variants: content.variants,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                </div>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  我确认将所选内容恢复成新稿，并重新审核
                </label>
                <Button
                  variant="secondary"
                  disabled={
                    busy ||
                    locked ||
                    draftDirty ||
                    !confirmed ||
                    selected.revision === content.revision
                  }
                  onClick={() =>
                    action(
                      () =>
                        api(
                          `/content/packages/${content.id}/restore/${selected.revision}`,
                          post({
                            expected_revision: content.revision,
                            confirmed: true,
                          }),
                        ),
                      "已恢复为新版本，请重新审核",
                    )
                  }
                >
                  恢复所选版本
                </Button>
              </>
            )}
          </section>
          <section>
            <h3>分平台文案</h3>
            {draftDirty && (
              <p role="status">
                此平台有未保存文案，请先保存，再切换平台或恢复历史。
              </p>
            )}
            <p className="muted">
              这些是独立编辑的创作版本。所有版本均接受预审，审核后随 ZIP
              导出；请另行核对平台当前要求。
            </p>
            <select
              aria-label="平台文案"
              value={platform}
              disabled={draftDirty}
              onChange={(e) => setPlatform(e.target.value)}
            >
              {Object.entries(platformName).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <form
              className="form-stack"
              onChange={() => {
                setDraftDirty(true);
                onDraftChange(true);
              }}
              key={`${content.id}-${content.revision}-${platform}`}
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                action(
                  () =>
                    api(`/content/packages/${content.id}`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        expected_revision: content.revision,
                        variants: {
                          ...content.variants,
                          [platform]: {
                            title: f.get("title"),
                            body: f.get("body"),
                            tags: String(f.get("tags"))
                              .split(/[,，]/)
                              .map((t) => t.trim())
                              .filter(Boolean),
                          },
                        },
                      }),
                    }),
                  "平台文案已保存，需要重新审核",
                );
              }}
            >
              <Field label="此平台标题">
                <input
                  name="title"
                  defaultValue={variant?.title || content.title}
                  required
                  maxLength={180}
                  disabled={locked}
                />
              </Field>
              <Field label="此平台正文">
                <textarea
                  name="body"
                  rows={5}
                  defaultValue={variant?.body || content.body}
                  required
                  maxLength={12000}
                  disabled={locked}
                />
              </Field>
              <Field label="话题（逗号分隔，最多十个）">
                <input
                  name="tags"
                  defaultValue={variant?.tags.join(", ") || ""}
                  disabled={locked}
                />
              </Field>
              <Button type="submit" disabled={busy || locked}>
                保存平台版本
              </Button>
            </form>
          </section>
        </div>
      </details>
    </Card>
  );
}

export function BrandChanges({
  brand,
  action,
  busy,
}: Actions & { brand: Brand }) {
  const [list, setList] = useState<Change[]>([]);
  const [error, setError] = useState("");
  const [released, setReleased] = useState<Record<string, boolean>>({});
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    api<Change[]>(`/brands/${brand.id}/changes`)
      .then(setList)
      .catch((e) => setError(e.message));
  }, [brand.id, brand.revision, refresh]);
  return (
    <Card>
      <h2>版本变更待核实区</h2>
      <p>
        将版本说明中的变化提交为提案。确认实际已经上线并核实来源之后，才能成为创作事实；这里不会自动扫描私有仓库。
      </p>
      {error && <p role="alert">{error}</p>}
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action(async () => {
            await api(
              `/brands/${brand.id}/changes`,
              post({
                claim: f.get("claim"),
                source: f.get("source"),
                product_version: f.get("version"),
              }),
            );
            setRefresh((v) => v + 1);
          }, "已保存为待核实提案");
        }}
      >
        <Field label="发现的功能变化">
          <textarea required name="claim" maxLength={1000} rows={2} />
        </Field>
        <Field label="证据来源">
          <input name="source" required maxLength={2000} />
        </Field>
        <Field label="适用产品版本">
          <input name="version" required maxLength={100} />
        </Field>
        <Button disabled={busy} type="submit">
          提交待核实变化
        </Button>
      </form>
      <div className="divider" />
      {list.length === 0 && <p className="muted">没有待核实变化。</p>}
      {list.map((c) => (
        <section key={c.id} className="subtle-note">
          <Badge>
            {c.status === "proposed"
              ? "待核实"
              : c.status === "verified"
                ? "已核实"
                : "已拒绝"}
          </Badge>
          <h3>{c.claim}</h3>
          <p>
            {c.product_version} · {c.source}
          </p>
          {c.status === "proposed" && (
            <>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={!!released[c.id]}
                  onChange={(e) =>
                    setReleased({ ...released, [c.id]: e.target.checked })
                  }
                />
                我确认此功能已上线，并已核实上述来源
              </label>
              <div className="form-actions">
                {["verified", "rejected"].map((decision) => (
                  <Button
                    variant="secondary"
                    key={decision}
                    disabled={
                      busy || (decision === "verified" && !released[c.id])
                    }
                    onClick={() =>
                      action(
                        async () => {
                          await api(
                            `/brands/${brand.id}/changes/${c.id}/decide`,
                            post({
                              decision,
                              released: !!released[c.id],
                              confirmed: true,
                              expected_brand_revision: brand.revision,
                            }),
                          );
                          setRefresh((v) => v + 1);
                        },
                        decision === "verified"
                          ? "已纳入事实，相关待发布稿需重新审核"
                          : "已拒绝提案",
                      )
                    }
                  >
                    {decision === "verified" ? "批准为事实" : "拒绝提案"}
                  </Button>
                ))}
              </div>
            </>
          )}
        </section>
      ))}
    </Card>
  );
}
