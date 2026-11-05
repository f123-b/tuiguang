"use client";
import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  CheckCheck,
  ChevronRight,
  Copy,
  ExternalLink,
  FolderOpen,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api, post } from "../../lib/api";

import {
  dateText,
  Field,
  PageHeader,
  platformName,
  type PageProps,
} from "../page-shared";
export function PublishPage({ store, action, busy, path }: PageProps) {
  const [selected, setSelected] = useState(path.split("/")[3] || "");
  const [checks, setChecks] = useState<boolean[]>([
    false,
    false,
    false,
    false,
    false,
  ]);
  const handoff =
    store.handoffs.find((h) => h.id === selected) || store.handoffs[0];
  const publication = store.publications.find(
    (p) => p.package_id === handoff?.id,
  );
  const official: Record<string, string> = {
    xiaohongshu: "https://www.xiaohongshu.com/",
    douyin: "https://www.douyin.com/",
    bilibili: "https://www.bilibili.com/",
  };
  return (
    <>
      <PageHeader
        eyebrow="MANUAL PUBLICATION"
        title="素材准备好了，分享由你决定"
        description="下载内容与素材，在平台官方页面亲自上传发布，完成后回来登记。"
      />
      <div className="info-strip">
        <ShieldCheck size={19} />
        <span>
          此处准备发布资料。上传与最终发布，由你在第三方平台亲自完成。
        </span>
      </div>
      {!store.handoffs.length ? (
        <Card>
          <EmptyState
            title="还没有准备好的发布包"
            description="打开一份草稿，完成事实与合规复核后，就可以生成真实的 ZIP 素材包。"
            action={
              <Link className="button primary" href="/campaigns">
                去审核内容
                <ArrowRight size={15} />
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="publish-columns">
          <div>
            <div className="package-list">
              {store.handoffs.map((h) => (
                <button
                  className={`package-select ${handoff.id === h.id ? "selected" : ""}`}
                  key={h.id}
                  onClick={() => {
                    setSelected(h.id);
                    setChecks([false, false, false, false, false]);
                  }}
                >
                  <span className="package-icon">
                    <FolderOpen size={24} />
                  </span>
                  <div>
                    <strong>{h.snapshot.title}</strong>
                    <p>
                      {platformName[h.platform]} · V{h.content_revision}
                    </p>
                  </div>
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
            <Card>
              <div className="section-heading">
                <h2>{handoff.snapshot.title}</h2>
                <Badge>{platformName[handoff.platform]}</Badge>
              </div>
              <div className="copy-box">
                <small>标题与正文</small>
                <h3>{handoff.snapshot.title}</h3>
                <p>{handoff.snapshot.body}</p>
              </div>
              <div className="form-actions">
                <a
                  className="button primary"
                  href={`/api/v1/manual-publication/packages/${handoff.id}/download`}
                >
                  <ArrowDownToLine size={16} />
                  下载素材包
                </a>
                <Button
                  variant="secondary"
                  onClick={() =>
                    action(async () => {
                      await navigator.clipboard.writeText(
                        `${handoff.snapshot.title}\n\n${handoff.snapshot.body}`,
                      );
                    }, "文案已复制")
                  }
                >
                  <Copy size={15} />
                  复制文案
                </Button>
                <a
                  href={official[handoff.platform]}
                  rel="noopener noreferrer"
                  target="_blank"
                  className="button quiet"
                >
                  打开官方平台
                  <ExternalLink size={14} />
                </a>
              </div>
              <p className="muted">
                ZIP 包含 PNG
                封面、文案、事实来源和发布检查表。官方页面的具体步骤与标识要求，请以发布时实际界面为准。
              </p>
            </Card>
          </div>
          <Card>
            <h2>
              {publication ? "已保存你的发布登记" : "发布前，最后确认一次"}
            </h2>
            {publication ? (
              <>
                <div className="record-success">
                  <CheckCheck size={30} />
                  <h3>用户登记已发布</h3>
                  <p>{dateText(publication.published_at)}</p>
                </div>
                <div className="alert">用户自行登记，未经平台验证。</div>
                {publication.url && (
                  <a
                    className="text-link"
                    href={publication.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    打开登记链接
                    <ExternalLink size={14} />
                  </a>
                )}
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    action(
                      () =>
                        api(`/manual-publication/records/${publication.id}`, {
                          method: "DELETE",
                        }),
                      "已撤销登记；第三方作品仍由你管理",
                    )
                  }
                >
                  撤销本次登记
                </Button>
              </>
            ) : (
              <>
                <div className="publish-checks">
                  {[
                    "产品信息与实际功能一致",
                    "已核对素材版权与使用授权",
                    "已检查平台当前发布规则",
                    "已按平台要求声明 AI 内容",
                    "我已在官方平台亲自上传并发布",
                  ].map((label, i) => (
                    <label className="checkline" key={label}>
                      <input
                        type="checkbox"
                        checked={checks[i]}
                        onChange={(e) =>
                          setChecks(
                            checks.map((c, n) =>
                              n === i ? e.target.checked : c,
                            ),
                          )
                        }
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <form
                  className="form-stack"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    action(
                      () =>
                        api(
                          "/manual-publication/records",
                          post({
                            package_id: handoff.id,
                            published_at: new Date(
                              String(f.get("published_at")),
                            ).toISOString(),
                            url: f.get("url"),
                            notes: f.get("notes"),
                            checklist: checks,
                          }),
                        ),
                      "已保存你的发布记录（用户自行登记，未经平台验证）",
                    );
                  }}
                >
                  <Field label="实际发布时间">
                    <input
                      name="published_at"
                      type="datetime-local"
                      required
                      defaultValue={new Date(
                        Date.now() - new Date().getTimezoneOffset() * 60000,
                      )
                        .toISOString()
                        .slice(0, 16)}
                    />
                  </Field>
                  <Field label="平台作品链接（可选）">
                    <input name="url" type="url" placeholder="https://" />
                  </Field>
                  <Field label="备注（可选）">
                    <textarea name="notes" rows={2} maxLength={2000} />
                  </Field>
                  <Button
                    type="submit"
                    disabled={busy || !checks.every(Boolean)}
                  >
                    <CheckCheck size={16} />
                    我已手动发布
                  </Button>
                  <small className="muted">用户自行登记，未经平台验证。</small>
                </form>
              </>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
