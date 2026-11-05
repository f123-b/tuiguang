"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import { Activity, BookOpen, Gauge } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, post } from "../../lib/api";

import { PageHeader, type PageProps } from "../page-shared";
export function SettingsPage({ store, action, busy }: PageProps) {
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  useEffect(() => {
    api<Record<string, unknown>>("/settings")
      .then(setSettings)
      .catch(() => {});
  }, []);
  return (
    <>
      <PageHeader
        title="清楚的设置，安心的创作"
        description="本地开发版。模型服务通过服务端环境配置管理，密钥不会出现在浏览器中。"
      />
      <div className="form-columns">
        <Card>
          <h2>模型与费用</h2>
          <div className="setting-row">
            <span>当前生成模式</span>
            <Badge tone="blue">
              {store.dashboard.generation_mode === "template"
                ? "本地规则草稿"
                : "真实 AI 模型"}
            </Badge>
          </div>
          <div className="setting-row">
            <span>模型</span>
            <span>{String(settings.model_id || "未配置")}</span>
          </div>
          <div className="setting-row">
            <span>模型密钥</span>
            <span>
              {settings.model_key_configured
                ? "已配置（不显示原文）"
                : "未配置"}
            </span>
          </div>
          <p>
            若需启用真实模型，请按仓库 README
            配置费用参数与模型服务，并在创作者设置中确认发送品牌事实的授权。
          </p>
          <Link className="button secondary" href="/creator/edit">
            <Gauge size={16} />
            管理预算与授权
          </Link>
        </Card>
        <Card>
          <h2>工作区与数据</h2>
          <div className="setting-row">
            <span>账号</span>
            <span>{store.user.email}</span>
          </div>
          <div className="setting-row">
            <span>存储</span>
            <span>工作区本地磁盘</span>
          </div>
          <div className="setting-row">
            <span>版本</span>
            <Badge>0.2.0-dev</Badge>
          </div>
          <p>
            数据保存在当前软件环境中。云端存储、订阅支付和完整备份界面尚未接入。
          </p>
          <div className="form-actions">
            <Link className="button secondary" href="/ops/diagnostics">
              <Activity size={15} />
              诊断与维护
            </Link>
            <Link className="button quiet" href="/help">
              <BookOpen size={15} />
              使用帮助
            </Link>
          </div>
          <Button
            variant="quiet"
            disabled={busy}
            onClick={() =>
              action(() => api("/auth/logout", post()), "已退出登录")
            }
          >
            退出当前会话
          </Button>
        </Card>
      </div>
    </>
  );
}

export function OpsPage({ path }: PageProps) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState("");
  const release = path.includes("releases");
  useEffect(() => {
    api(release ? "/releases/current" : "/ops/diagnostics")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [release]);
  return (
    <>
      <PageHeader
        title={release ? "运行版本清单" : "诊断与维护"}
        description="只展示当前工作区的脱敏事件与真实运行版本。"
      />
      <div className="tabs">
        <Link className={!release ? "selected" : ""} href="/ops/diagnostics">
          任务追踪
        </Link>
        <Link className={release ? "selected" : ""} href="/ops/releases">
          版本清单
        </Link>
      </div>
      <Card>
        {error ? (
          <div role="alert">{error}</div>
        ) : data ? (
          <pre className="diagnostic-json">{JSON.stringify(data, null, 2)}</pre>
        ) : (
          <p>正在读取…</p>
        )}
      </Card>
    </>
  );
}
