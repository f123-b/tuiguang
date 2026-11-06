"use client";
import { Button, Card } from "@xuliu/ui";
import Link from "next/link";
import { api, post } from "../../lib/api";
import { PageHeader, type PageProps } from "../page-shared";
import { SystemSettings } from "./system-settings";
export { OpsConsole as OpsPage } from "./ops-console";
export function SettingsPage(props: PageProps) {
  return (
    <>
      <PageHeader
        title="清楚的设置，安心的创作"
        description="密钥加密保存在服务端，保存配置不发起模型请求。"
      />
      <SystemSettings {...props} />
      <Card>
        <h2>当前账号</h2>
        <p>
          {props.store.user.email} · {props.store.user.role}
        </p>
        <div className="form-actions">
          <Link href="/help" className="button secondary">
            使用帮助
          </Link>
          <Link href="/ops/diagnostics" className="button quiet">
            诊断与维护
          </Link>
          <Button
            variant="quiet"
            disabled={props.busy}
            onClick={() =>
              props.action(() => api("/auth/logout", post()), "已退出登录")
            }
          >
            退出当前会话
          </Button>
        </div>
      </Card>
    </>
  );
}
