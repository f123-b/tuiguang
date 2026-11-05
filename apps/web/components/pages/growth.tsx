"use client";
import { Badge, Card, EmptyState } from "@xuliu/ui";
import { ArrowRight, CheckCheck, CircleHelp, Sprout } from "lucide-react";
import Link from "next/link";

import { PageHeader, type PageProps } from "../page-shared";
export function GrowthPage({ store }: PageProps) {
  return (
    <>
      <PageHeader
        eyebrow="GROW WITH EVIDENCE"
        title="每一次迭代，都从真实反馈开始"
        description="区分观察到的事实与待验证的假设，让下一个方向有迹可循。"
      />
      <div className="three-grid">
        <Card>
          <span className="insight-icon mint">
            <CheckCheck size={22} />
          </span>
          <h2>观察到的事实</h2>
          <p>
            已经准备 {store.contents.length} 篇内容，用户登记{" "}
            {store.publications.length} 次发布，导入{" "}
            {store.analytics.snapshot_count} 条指标快照。
          </p>
          <Badge tone="success">本软件持久化记录</Badge>
        </Card>
        <Card>
          <span className="insight-icon amber">
            <CircleHelp size={22} />
          </span>
          <h2>尚不能确定</h2>
          <p>现有数据不能证明平台算法偏好，也不能对流量和转化作因果判断。</p>
          <Badge tone="warning">证据仍需积累</Badge>
        </Card>
        <Card>
          <span className="insight-icon blue">
            <Sprout size={22} />
          </span>
          <h2>下一步可以做</h2>
          <p>
            持续记录相同统计窗口的指标与人工反馈，复核内容事实，再比较具体表达方式。
          </p>
          <Link href="/analytics/import" className="text-link">
            补充真实数据
            <ArrowRight size={14} />
          </Link>
        </Card>
      </div>
      <Card>
        <EmptyState
          title="AI 周报与策略学习，待下一阶段接入"
          description="当前已实现来源与窗口分组查询，尚未生成学习结论或自动修改策略。"
        />
      </Card>
    </>
  );
}
