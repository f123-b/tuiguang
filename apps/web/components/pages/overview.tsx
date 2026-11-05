"use client";
import { Badge, Button, Card, EmptyState, StatusBadge } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronRight,
  FileText,
  Gauge,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { api, post } from "../../lib/api";

import { money, PageHeader, type PageProps } from "../page-shared";
import { ContentCard } from "./content";
export function Overview({ store, action, busy }: PageProps) {
  const creator = store.creators[0];
  const counts = store.dashboard.counts;
  const date = new Date().toLocaleDateString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "long",
    day: "numeric",
    weekday: "long",
  });
  const run = () =>
    creator &&
    action(
      () =>
        api(`/creators/${creator.id}/run-today`, {
          ...post(),
          headers: { "Idempotency-Key": crypto.randomUUID() },
        }),
      "今日任务已保存，后台将开始制作",
    );
  return (
    <>
      <PageHeader
        eyebrow="YOUR CREATIVE WORKSPACE"
        title="让产品的故事，持续发生。"
        description="从一个真实的想法，到一份值得分享的内容。"
      >
        <span className="date-label">{date}</span>
        {creator && <StatusBadge status={creator.status} />}
      </PageHeader>
      <div className="overview-banner">
        <div className="banner-copy">
          <span className="eyebrow mint">
            <span className="live-dot active" />
            创作有序进行
          </span>
          <h2>
            {creator
              ? `${creator.name}，为下一次分享做准备`
              : "认识你的第一位 AI 内容伙伴"}
          </h2>
          <p>
            {creator
              ? "选题、草稿、素材，在这里逐步就绪。最后的审核和分享，由你决定。"
              : "添加真实品牌资料，设定创作节奏，让每一次表达都有据可依。"}
          </p>
          <div className="row">
            {creator ? (
              <Button
                disabled={busy || creator.status !== "active"}
                onClick={run}
              >
                <Play size={15} />
                准备今日内容
              </Button>
            ) : (
              <Link href="/brand" className="button primary">
                开始设置工作空间 <ArrowRight size={15} />
              </Link>
            )}
            <Link className="text-link" href={creator ? "/creator" : "/help"}>
              {creator ? "查看创作者" : "了解创作流程"}
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="orbital o1" />
          <div className="orbital o2" />
          <div className="art-tile tile-back">
            <FileText size={30} />
            <span>真实的产品故事</span>
            <i />
            <i />
          </div>
          <div className="art-tile tile-front">
            <Sparkles size={25} />
            <span>
              每一次创作
              <br />
              <b>都有新的可能</b>
            </span>
          </div>
          <span className="art-spark s1">✦</span>
          <span className="art-spark s2">✧</span>
        </div>
      </div>
      <div className="stats-grid">
        {[
          {
            title: "已准备内容",
            value: counts.contents,
            suffix: "篇",
            icon: FileText,
            note: "来自真实创作任务",
            cls: "blue",
          },
          {
            title: "等待你的审核",
            value: counts.awaiting_review,
            suffix: "篇",
            icon: ShieldCheck,
            note: "好的内容，值得再看一眼",
            cls: "purple",
          },
          {
            title: "待手动发布",
            value: counts.awaiting_manual,
            suffix: "份",
            icon: ArrowDownToLine,
            note: "素材就绪，由你亲自分享",
            cls: "mint",
          },
          {
            title: "已记录创作费用",
            value: money(store.dashboard.spent_cents),
            suffix: "",
            icon: Gauge,
            note: "模型费用，不含本地算力",
            cls: "amber",
          },
        ].map((s) => (
          <Card className="stat-card" key={s.title}>
            <div className="stat-label">
              {s.title}
              <span className={`stat-icon ${s.cls}`}>
                <s.icon size={17} />
              </span>
            </div>
            <div className="stat-value">
              {s.value}
              <small>{s.suffix}</small>
            </div>
            <p>{s.note}</p>
          </Card>
        ))}
      </div>
      <div className="overview-columns">
        <Card>
          <div className="section-heading">
            <h2>今日创作流程</h2>
            <Link href="/creator/activity">
              运行详情
              <ChevronRight size={14} />
            </Link>
          </div>
          <div className="workflow">
            {[
              ["选择选题", "依据品牌事实，准备内容方向", store.runs.length > 0],
              [
                "制作内容",
                store.dashboard.generation_mode === "template"
                  ? "当前使用本地规则草稿"
                  : "AI 准备文案与结构",
                store.contents.length > 0,
              ],
              [
                "审核与打包",
                "检查事实、素材与 AI 标识",
                store.handoffs.length > 0,
              ],
              [
                "由你手动发布",
                "下载资料，在官方平台亲自发布",
                store.publications.length > 0,
              ],
            ].map(([title, desc, done], i) => (
              <div
                className={`workflow-step ${done ? "done" : ""}`}
                key={String(title)}
              >
                <span className="step-icon">
                  {done ? <Check size={15} /> : String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <strong>{title as string}</strong>
                  <p>{desc as string}</p>
                </div>
                <span>{done ? "已完成" : "待进行"}</span>
              </div>
            ))}
          </div>
          <div className="subtle-note">
            <ShieldCheck size={14} />
            发布操作由你在第三方官方平台完成
          </div>
        </Card>
        <Card>
          <div className="section-heading">
            <h2>需要你关注</h2>
            <Badge tone="warning">
              {counts.awaiting_review + counts.awaiting_manual} 项
            </Badge>
          </div>
          <div className="todo-list">
            <Link href="/campaigns">
              <span className="todo-icon purple">
                <FileText size={19} />
              </span>
              <div>
                <strong>检查待审阅的内容</strong>
                <p>
                  {counts.awaiting_review
                    ? `${counts.awaiting_review} 篇草稿，等待你的意见`
                    : "内容准备好后，会出现在这里"}
                </p>
              </div>
              <ChevronRight size={16} />
            </Link>
            <Link href="/publish">
              <span className="todo-icon mint">
                <ArrowDownToLine size={19} />
              </span>
              <div>
                <strong>带着素材去分享</strong>
                <p>
                  {counts.awaiting_manual
                    ? `${counts.awaiting_manual} 份资料可以下载`
                    : "审核通过后，即可准备发布包"}
                </p>
              </div>
              <ChevronRight size={16} />
            </Link>
            <Link href="/analytics/import">
              <span className="todo-icon blue">
                <Gauge size={19} />
              </span>
              <div>
                <strong>让反馈成为下一步的依据</strong>
                <p>
                  {store.analytics.snapshot_count
                    ? `已导入 ${store.analytics.snapshot_count} 条指标快照`
                    : "尚未导入平台数据"}
                </p>
              </div>
              <ChevronRight size={16} />
            </Link>
          </div>
          <Link href="/calendar" className="calendar-shortcut">
            <CalendarDays size={17} />
            <span>看看接下来的创作计划</span>
            <ArrowRight size={15} />
          </Link>
        </Card>
      </div>
      <div className="section-heading outside">
        <div>
          <h2>最近的内容</h2>
          <p>每一个产品，都有值得被讲述的一面。</p>
        </div>
        <Link href="/campaigns">
          查看全部
          <ArrowRight size={14} />
        </Link>
      </div>
      {store.contents.length ? (
        <div className="content-grid">
          {store.contents.slice(0, 3).map((c) => (
            <ContentCard key={c.id} content={c} />
          ))}
        </div>
      ) : (
        <Card>
          <EmptyState
            title="你的第一篇内容，从这里开始"
            description={
              store.brands.length
                ? "创建创作者并准备今日内容，真实草稿会出现在这里。"
                : "先添加产品介绍和有来源的功能信息，让每一次创作都有依据。"
            }
            action={
              <Link
                className="button secondary"
                href={store.brands.length ? "/creator" : "/brand"}
              >
                {store.brands.length ? "设置创作者" : "添加品牌资料"}
                <ArrowRight size={14} />
              </Link>
            }
          />
        </Card>
      )}
    </>
  );
}
