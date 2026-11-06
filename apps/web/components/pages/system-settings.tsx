"use client";
import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post } from "../../lib/api";
import { Field, PageHeader, type PageProps } from "../page-shared";

type Model = {
  revision: number;
  mode: string;
  model_id: string | null;
  model_revision: string | null;
  base_url: string;
  input_price: number | null;
  output_price: number | null;
  max_tokens: number;
  price_source: string;
  key_configured: boolean;
  source: string;
};
type Preference = {
  notification_mode: string;
  timezone: string;
  digest_hour: number;
};
type Billing = {
  actual_cents: number;
  unsettled_reserved_cents: number;
  ledgers: {
    id: string;
    run_id: string;
    status: string;
    actual_cents: number | null;
    reserved_cents: number;
  }[];
};

export function SystemSettings({ store, action, busy }: PageProps) {
  const [model, setModel] = useState<Model | null>(null),
    [preferences, setPreferences] = useState<Preference | null>(null),
    [billing, setBilling] = useState<Billing | null>(null),
    [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    Promise.all([
      api<Model>("/settings/models"),
      api<Preference>("/settings/preferences"),
      api<Billing>("/settings/billing"),
    ])
      .then(([m, p, b]) => {
        setModel(m);
        setPreferences(p);
        setBilling(b);
      })
      .catch((e) => setError(e.message));
  }, [refresh]);
  return (
    <>
      {error && <p role="alert">{error}</p>}
      <div className="form-columns">
        <Card>
          <h2>模型配置与密钥</h2>
          <p>
            密钥加密保存在服务端，页面不会回显已保存密钥。保存不调用模型；生成还需创作者授权和预算。修改配置后，尚未开始的旧模型任务会明确阻断。
          </p>
          {model ? (
            <form
              className="form-stack"
              key={model.revision}
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const key = String(f.get("api_key") || "");
                action(async () => {
                  const result = await api<Model>("/settings/models", {
                    method: "PUT",
                    body: JSON.stringify({
                      expected_revision: model.revision,
                      mode:
                        f.get("clear_key") === "on"
                          ? "template"
                          : f.get("mode"),
                      model_id: f.get("model"),
                      model_revision:
                        String(f.get("model_revision") || "") || null,
                      base_url: f.get("base_url"),
                      input_price: Number(f.get("input_price")),
                      output_price: Number(f.get("output_price")),
                      max_tokens: Number(f.get("max_tokens")),
                      price_source: f.get("price_source"),
                      ...(key ? { api_key: key } : {}),
                      clear_key: f.get("clear_key") === "on",
                    }),
                  });
                  setModel(result);
                }, "模型配置已加密保存；没有发起收费请求");
              }}
            >
              <Field label="生成方式">
                <select name="mode" defaultValue={model.mode}>
                  <option value="template">本地规则草稿</option>
                  <option value="openai">真实模型网关</option>
                </select>
              </Field>
              <Field label="模型名称">
                <input
                  name="model"
                  defaultValue={model.model_id || ""}
                  maxLength={120}
                />
              </Field>
              <Field label="模型修订（可选）">
                <input
                  name="model_revision"
                  defaultValue={model.model_revision || ""}
                  maxLength={120}
                />
              </Field>
              <Field label="允许的模型 HTTPS 地址">
                <input
                  name="base_url"
                  type="url"
                  defaultValue={model.base_url}
                  required
                  maxLength={1000}
                />
              </Field>
              <Field
                label={
                  model.key_configured ? "更新密钥（留空保留）" : "模型密钥"
                }
              >
                <input
                  name="api_key"
                  type="password"
                  autoComplete="new-password"
                  maxLength={4000}
                />
              </Field>
              <label className="checkline">
                <input type="checkbox" name="clear_key" />
                清除工作区密钥（同时切回本地规则草稿）
              </label>
              <div className="form-grid">
                <Field label="输入价格：分 / 百万 Token">
                  <input
                    name="input_price"
                    type="number"
                    min={0}
                    required
                    defaultValue={model.input_price ?? 0}
                  />
                </Field>
                <Field label="输出价格：分 / 百万 Token">
                  <input
                    name="output_price"
                    type="number"
                    min={0}
                    required
                    defaultValue={model.output_price ?? 0}
                  />
                </Field>
                <Field label="最大输出 Token">
                  <input
                    name="max_tokens"
                    type="number"
                    min={128}
                    max={8000}
                    defaultValue={model.max_tokens}
                    required
                  />
                </Field>
              </div>
              <Field label="价格来源与核验说明">
                <textarea
                  name="price_source"
                  required
                  rows={2}
                  maxLength={2000}
                  defaultValue={model.price_source}
                />
              </Field>
              <Badge>
                {model.key_configured ? "密钥已配置（不回显）" : "没有密钥"}
              </Badge>
              <Button
                type="submit"
                disabled={busy || !["owner", "admin"].includes(store.user.role)}
              >
                保存模型设置
              </Button>
            </form>
          ) : (
            <p>读取模型设置中…</p>
          )}
        </Card>
        <div>
          <Card>
            <h2>站内提醒偏好</h2>
            {preferences && (
              <form
                className="form-stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  action(async () => {
                    setPreferences(
                      await api<Preference>("/settings/preferences", {
                        method: "PUT",
                        body: JSON.stringify({
                          notification_mode: f.get("mode"),
                          timezone: f.get("timezone"),
                          digest_hour: Number(f.get("hour")),
                        }),
                      }),
                    );
                  }, "提醒偏好已保存");
                }}
              >
                <Field label="通知频率">
                  <select
                    name="mode"
                    defaultValue={preferences.notification_mode}
                  >
                    <option value="instant">及时站内提醒</option>
                    <option value="daily">每天汇总一次</option>
                    <option value="off">关闭新提醒</option>
                  </select>
                </Field>
                <Field label="提醒时区">
                  <input
                    name="timezone"
                    defaultValue={preferences.timezone}
                    required
                  />
                </Field>
                <Field label="每日汇总小时">
                  <input
                    name="hour"
                    type="number"
                    min={0}
                    max={23}
                    defaultValue={preferences.digest_hour}
                    required
                  />
                </Field>
                <Button type="submit" disabled={busy}>
                  保存提醒偏好
                </Button>
              </form>
            )}
            <p className="muted">
              提醒保留在本软件内，不发送社媒私信。关闭后保留已有通知，计划中的提醒在重新启用后检查。
            </p>
            <Link href="/notifications" className="text-link">
              查看通知中心
            </Link>
          </Card>
          <Card>
            <h2>隐私与工作区导出</h2>
            <p>
              下载当前工作区记录，用于自行保存。导出不含登录会话、密码或模型密钥，不是待发布资料包。包含素材时最多
              200 MB；授权状态仍需复核。
            </p>
            <div className="form-actions">
              <a className="button secondary" href="/api/v1/settings/export">
                导出私有记录 ZIP
              </a>
              <a
                className="button quiet"
                href="/api/v1/settings/export?include_files=true"
              >
                记录与原始素材
              </a>
            </div>
            <p className="muted">
              服务器备份还需由操作者独立保管主密钥；此下载不能代替完整灾备。云存储和订阅支付没有接通，也不会收取订阅费用。
            </p>
          </Card>
          <Card>
            <h2>费用账本</h2>
            {billing && (
              <>
                <p>
                  已结算 {(billing.actual_cents / 100).toFixed(2)}{" "}
                  元；结果待核对的预留{" "}
                  {(billing.unsettled_reserved_cents / 100).toFixed(2)} 元。
                </p>
                <p className="muted">
                  根据提供者使用回执与用户配置价格计算，不是提供者正式账单。本地
                  CPU 能耗未估价。
                </p>
                {billing.ledgers
                  .filter(
                    (l) =>
                      l.status === "reserved" &&
                      l.actual_cents === null &&
                      store.runs.some(
                        (r) => r.id === l.run_id && r.status === "failed",
                      ),
                  )
                  .map((l) => (
                    <form
                      key={l.id}
                      className="form-stack subtle-note"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = new FormData(e.currentTarget);
                        action(async () => {
                          await api(
                            `/settings/billing/${l.id}/reconcile`,
                            post({
                              confirmed: true,
                              actual_cents: Number(f.get("cents")),
                              result: f.get("result"),
                              provider_receipt_source: f.get("source"),
                            }),
                          );
                          setRefresh((v) => v + 1);
                        }, "费用已按用户提供依据核对；旧请求不会重试，请手动恢复创作者");
                      }}
                    >
                      <h3>核对未知回执</h3>
                      <p className="muted">
                        任务 {l.run_id} · 预留 {l.reserved_cents}{" "}
                        分。请先自行核对提供者账单；这里保存用户自报依据，不能代替提供者确认。
                      </p>
                      <Field label="核对结果">
                        <select name="result">
                          <option value="not_charged">未收费</option>
                          <option value="charged">已收费</option>
                        </select>
                      </Field>
                      <Field label="实际金额（整数分）">
                        <input
                          name="cents"
                          type="number"
                          min={0}
                          max={10000000}
                          defaultValue={0}
                          required
                        />
                      </Field>
                      <Field label="账单或核对依据">
                        <textarea name="source" maxLength={2000} required />
                      </Field>
                      <label className="checkline">
                        <input type="checkbox" required />
                        我已核对这一次请求的账单，并确认录入结果。
                      </label>
                      <Button type="submit" disabled={busy}>
                        保存人工核对
                      </Button>
                    </form>
                  ))}
                <details>
                  <summary>查看逐任务整数分账本</summary>
                  <pre className="diagnostic-json">
                    {JSON.stringify(billing.ledgers, null, 2)}
                  </pre>
                </details>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

type Notice = {
  id: string;
  kind: string;
  title: string;
  body: string;
  action_path: string;
  created_at: string;
  read_at: string | null;
};
type Reminder = {
  id: string;
  package_id: string;
  due_at: string;
  state: string;
};

export function NotificationsPage({ store, action, busy }: PageProps) {
  const [notes, setNotes] = useState<Notice[]>([]),
    [reminders, setReminders] = useState<Reminder[]>([]),
    [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    Promise.all([
      api<Notice[]>("/notifications"),
      api<Reminder[]>("/notifications/reminders"),
    ])
      .then(([n, r]) => {
        setNotes(n);
        setReminders(r);
      })
      .catch((e) => setError(e.message));
  }, [refresh]);
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      setRefresh((v) => v + 1);
    }, message);
  return (
    <>
      <PageHeader
        title="创作待办，有事才提醒"
        description="站内通知持久保存。仅提醒你处理自己的内容，不访问第三方账号。"
      >
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() =>
            run(
              () => api("/notifications/sync", post()),
              "已检查当前工作区待办",
            )
          }
        >
          检查待办
        </Button>
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() =>
            run(() => api("/notifications/read-all", post()), "全部标为已读")
          }
        >
          全部已读
        </Button>
        <Link className="button quiet" href="/settings">
          提醒设置
        </Link>
      </PageHeader>
      {error && <p role="alert">{error}</p>}
      {notes.length ? (
        notes.map((n) => (
          <Card key={n.id}>
            <div className="section-heading">
              <h3>{n.title}</h3>
              <Badge tone={n.read_at ? "neutral" : "blue"}>
                {n.read_at ? "已读" : "未读"}
              </Badge>
            </div>
            <p>{n.body}</p>
            <small className="muted">{n.created_at}</small>
            <div className="form-actions">
              <Link href={n.action_path} className="button secondary">
                查看相关内容
              </Link>
              {!n.read_at && (
                <Button
                  variant="quiet"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => api(`/notifications/${n.id}/read`, post()),
                      "已标为已读",
                    )
                  }
                >
                  标为已读
                </Button>
              )}
            </div>
          </Card>
        ))
      ) : (
        <Card>
          <EmptyState
            title="暂时没有通知"
            description="后台检查会按提醒偏好生成待办；也可点击“检查待办”。"
          />
        </Card>
      )}
      <Card>
        <h2>设置手动发布提醒</h2>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(
              () =>
                api(
                  "/notifications/reminders",
                  post({
                    package_id: f.get("package"),
                    due_at: new Date(String(f.get("due"))).toISOString(),
                    confirmed: true,
                  }),
                ),
              "提醒已保存，不会自动发布",
            );
          }}
        >
          <Field label="对应发布包">
            <select name="package" required>
              {store.handoffs.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.snapshot.title} · V{h.content_revision}
                </option>
              ))}
            </select>
          </Field>
          <Field label="提醒时间（当前设备时区）">
            <input name="due" type="datetime-local" required />
          </Field>
          <Button type="submit" disabled={busy || !store.handoffs.length}>
            保存提醒
          </Button>
        </form>
        {reminders.map((r) => (
          <div className="subtle-note" key={r.id}>
            <p>
              {r.due_at} ·{" "}
              {r.state === "scheduled"
                ? "等待提醒"
                : r.state === "delivered"
                  ? "已提醒"
                  : "已取消"}
            </p>
            <Link
              href={`/publish/package/${r.package_id}`}
              className="text-link"
            >
              查看发布包
            </Link>
            {r.state === "scheduled" && (
              <Button
                variant="quiet"
                disabled={busy}
                onClick={() =>
                  run(
                    () =>
                      api(`/notifications/reminders/${r.id}/dismiss`, post()),
                    "提醒已取消",
                  )
                }
              >
                取消提醒
              </Button>
            )}
          </div>
        ))}
      </Card>
    </>
  );
}
