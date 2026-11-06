"use client";
import { Badge, Button, Card } from "@xuliu/ui";
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
  endpoint_approved: boolean;
  json_mode: boolean;
  token_parameter: string;
};
type Check = {
  id: string;
  config_revision: number;
  kind: string;
  status: string;
  run_id: string | null;
  result: {
    models?: string[];
    error_code?: string;
    actual_cents?: number;
    usage?: unknown;
  };
};
const errors: Record<string, string> = {
  MODEL_KEY_REJECTED: "密钥被网关拒绝，请核对密钥和地址。",
  MODEL_ACCESS_DENIED: "网关拒绝访问，请检查权限。",
  MODEL_LIST_UNSUPPORTED: "这个网关没有模型列表接口，可手工填写模型名称。",
  MODEL_RATE_LIMITED: "网关触发限流，请稍后主动重试。",
  MODEL_CONNECTION_FAILED: "连接或回执格式检查失败，请检查地址与网络。",
  AGENT_PROVIDER_RESULT_UNKNOWN:
    "生成回执或费用未知，已停止重试，请先核对费用。",
};

export function ModelSettingsPage({ store, action, busy }: PageProps) {
  const [model, setModel] = useState<Model | null>(null),
    [checks, setChecks] = useState<Check[]>([]),
    [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0),
    [dirty, setDirty] = useState(false),
    [listConsent, setListConsent] = useState(false),
    [probeConsent, setProbeConsent] = useState(false);
  const runState = store.runs.map((r) => `${r.id}:${r.status}`).join("|");
  useEffect(() => {
    Promise.all([
      api<Model>("/settings/models"),
      api<Check[]>("/settings/models/checks"),
    ])
      .then(([m, c]) => {
        setModel(m);
        setChecks(c);
      })
      .catch((e) => setError(e.message));
  }, [refresh, runState]);
  const creator = store.creators[0];
  const admin = ["owner", "admin"].includes(store.user.role);
  const names = [
    ...new Set(
      checks
        .filter((c) => c.config_revision === model?.revision)
        .flatMap((c) => c.result.models || []),
    ),
  ];
  const run = (fn: () => Promise<unknown>, message: string) =>
    action(async () => {
      await fn();
      setRefresh((v) => v + 1);
    }, message);
  return (
    <>
      <PageHeader
        title="连接你自己的模型"
        description="支持 OpenAI 兼容接口。密钥只在本机服务端加密保存，保存配置不会发送模型请求。"
      >
        <Link className="button quiet" href="/settings">
          返回设置
        </Link>
      </PageHeader>
      {error && <p role="alert">{error}</p>}
      <div className="form-columns">
        <Card>
          <h2>网关、模型与密钥</h2>
          <p className="muted">
            可先保存地址和密钥、读取模型列表，再选择模型并启用。Base URL
            填接口根路径，例如 https://gateway.example.com/v1。
          </p>
          {model && (
            <form
              key={model.revision}
              className="form-stack"
              onChange={() => setDirty(true)}
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const key = String(f.get("api_key") || "");
                run(async () => {
                  const result = await api<Model>("/settings/models", {
                    method: "PUT",
                    body: JSON.stringify({
                      expected_revision: model.revision,
                      mode:
                        f.get("clear_key") === "on"
                          ? "template"
                          : f.get("mode"),
                      base_url: f.get("base_url"),
                      model_id: f.get("model"),
                      model_revision: String(f.get("revision") || "") || null,
                      input_price: Number(f.get("input_price")),
                      output_price: Number(f.get("output_price")),
                      max_tokens: Number(f.get("max_tokens")),
                      price_source: f.get("source"),
                      json_mode: f.get("json_mode") === "on",
                      token_parameter: f.get("token_parameter"),
                      endpoint_confirmed: f.get("trust") === "on",
                      clear_key: f.get("clear_key") === "on",
                      ...(key ? { api_key: key } : {}),
                    }),
                  });
                  setModel(result);
                  setDirty(false);
                  setListConsent(false);
                  setProbeConsent(false);
                }, "模型设置已保存；尚未发送请求");
              }}
            >
              <Field label="生成方式">
                <select name="mode" defaultValue={model.mode}>
                  <option value="template">本地规则草稿</option>
                  <option value="openai">已配置的真实模型</option>
                </select>
              </Field>
              <Field label="Base URL">
                <input
                  name="base_url"
                  type="url"
                  required
                  maxLength={1000}
                  defaultValue={model.base_url}
                />
              </Field>
              <label className="checkline">
                <input
                  type="checkbox"
                  name="trust"
                  defaultChecked={model.endpoint_approved}
                />
                我确认信任此网关地址，允许将模型密钥和授权输入发送到此地址。
              </label>
              <Field
                label={
                  model.key_configured
                    ? "API Key（留空保留；换地址须重新输入）"
                    : "API Key"
                }
              >
                <input
                  name="api_key"
                  type="password"
                  autoComplete="new-password"
                  maxLength={4000}
                />
              </Field>
              <Field label="模型名称">
                <input
                  name="model"
                  list="available-models"
                  maxLength={120}
                  defaultValue={model.model_id || ""}
                />
                <datalist id="available-models">
                  {names.map((n) => (
                    <option value={n} key={n} />
                  ))}
                </datalist>
              </Field>
              <Field label="模型版本备注（可选）">
                <input
                  name="revision"
                  maxLength={120}
                  defaultValue={model.model_revision || ""}
                />
              </Field>
              <div className="form-grid">
                <Field label="输入价格：分 / 百万 Token">
                  <input
                    name="input_price"
                    type="number"
                    min={0}
                    max={100000000}
                    required
                    defaultValue={model.input_price ?? 0}
                  />
                </Field>
                <Field label="输出价格：分 / 百万 Token">
                  <input
                    name="output_price"
                    type="number"
                    min={0}
                    max={100000000}
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
                    required
                    defaultValue={model.max_tokens}
                  />
                </Field>
              </div>
              <Field label="价格来源与核验说明">
                <textarea
                  name="source"
                  maxLength={2000}
                  required
                  defaultValue={model.price_source}
                />
              </Field>
              <details>
                <summary>兼容接口参数</summary>
                <p className="muted">
                  按你的网关文档选择。失败时不会自动换参数重发。
                </p>
                <label className="checkline">
                  <input
                    type="checkbox"
                    name="json_mode"
                    defaultChecked={model.json_mode}
                  />
                  请求 JSON Object 输出模式
                </label>
                <Field label="输出上限参数">
                  <select
                    name="token_parameter"
                    defaultValue={model.token_parameter}
                  >
                    <option value="max_tokens">max_tokens</option>
                    <option value="max_completion_tokens">
                      max_completion_tokens
                    </option>
                  </select>
                </Field>
              </details>
              <label className="checkline">
                <input name="clear_key" type="checkbox" />
                清除密钥并切回规则草稿
              </label>
              <Badge>
                {model.key_configured ? "密钥已保存，不回显" : "尚无工作区密钥"}
              </Badge>
              <Button type="submit" disabled={busy || !admin}>
                保存模型配置
              </Button>
            </form>
          )}
        </Card>
        <div>
          <Card>
            <h2>读取模型列表</h2>
            <p>
              只访问已保存网关的
              /models，不发送品牌资料或生成请求。部分网关没有此接口，仍可手工填写模型名称。
            </p>
            <label className="checkline">
              <input
                type="checkbox"
                checked={listConsent}
                onChange={(e) => setListConsent(e.target.checked)}
              />
              允许使用已保存密钥读取模型列表
            </label>
            <Button
              disabled={
                busy ||
                dirty ||
                !admin ||
                !model?.key_configured ||
                !listConsent
              }
              onClick={() =>
                model &&
                run(
                  () =>
                    api(
                      "/settings/models/check",
                      post({
                        expected_revision: model.revision,
                        confirmed: true,
                      }),
                    ),
                  "模型列表检查完成，请查看回执",
                )
              }
            >
              检查连接并读取模型
            </Button>
            {!!names.length && <p>可用模型：{names.join(" / ")}</p>}
            {dirty && <p role="status">先保存配置，再检查连接。</p>}
          </Card>
          <Card>
            <h2>实际生成联调</h2>
            <p>
              仅发送固定 JSON
              测试，不上传品牌资料。使用创作者日/月预算，最多输出 512
              Token。超时或未知费用不会自动重试。
            </p>
            {!creator ||
            creator.status !== "active" ||
            !creator.model_consent ? (
              <p>
                <Link className="text-link" href="/creator/edit">
                  先设置创作者的模型授权、预算和运行状态
                </Link>
              </p>
            ) : null}
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                if (!creator || !model) return;
                run(
                  () =>
                    api("/settings/models/probe", {
                      ...post({
                        creator_id: creator.id,
                        expected_revision: model.revision,
                        max_cost_cents: Number(f.get("cap")),
                        confirmed: true,
                      }),
                      headers: { "Idempotency-Key": crypto.randomUUID() },
                    }),
                  "固定输入联调已入队，请查看回执；不会生成日更内容",
                );
              }}
            >
              <Field label="本次确认预算上限（整数分）">
                <input
                  name="cap"
                  type="number"
                  min={1}
                  max={10000}
                  defaultValue={10}
                  required
                />
              </Field>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={probeConsent}
                  onChange={(e) => setProbeConsent(e.target.checked)}
                />
                我同意发送固定测试并使用上述预算
              </label>
              <Button
                type="submit"
                disabled={
                  busy ||
                  dirty ||
                  !admin ||
                  !probeConsent ||
                  model?.mode !== "openai" ||
                  creator?.status !== "active" ||
                  !creator?.model_consent
                }
              >
                开始一次生成联调
              </Button>
            </form>
          </Card>
        </div>
      </div>
      <Card>
        <h2>检查与联调回执</h2>
        {!checks.length && <p>尚未发起检查。保存配置不会自动测试。</p>}
        {checks.map((c) => (
          <section className="subtle-note" key={c.id}>
            <Badge>
              {c.kind === "generation" ? "生成联调" : "模型列表"} · {c.status}
            </Badge>
            <p>
              配置 V{c.config_revision}
              {c.config_revision !== model?.revision ? "（历史配置）" : ""}
              {c.result.actual_cents !== undefined
                ? ` · 实际 ${c.result.actual_cents} 分`
                : ""}
            </p>
            {c.result.error_code && (
              <p role="alert">
                {errors[c.result.error_code] || c.result.error_code}
              </p>
            )}
            <details>
              <summary>脱敏回执</summary>
              <pre className="diagnostic-json">
                {JSON.stringify(c, null, 2)}
              </pre>
            </details>
          </section>
        ))}
      </Card>
    </>
  );
}
