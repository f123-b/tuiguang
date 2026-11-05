import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet";
}) {
  return (
    <button {...props} className={`button ${variant} ${className}`}>
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "success" | "warning" | "neutral" | "danger" | "blue";
}) {
  return (
    <span className={`badge ${tone}`}>
      <span className="status-dot" />
      {children}
    </span>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-orbit">✦</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export const statusLabels: Record<string, string> = {
  active: "创作中",
  draft: "草稿",
  paused_by_user: "已暂停",
  paused_by_budget: "预算暂停",
  paused_by_error: "异常暂停",
  queued: "等待执行",
  running: "正在制作",
  completed: "已完成",
  failed: "执行失败",
  skipped: "已跳过",
  blocked: "需处理",
  awaiting_user_review: "待你审核",
  approved_for_handoff: "已人工审核",
  awaiting_manual_publication: "待手动发布",
  user_reported_published: "用户登记已发布",
  ready: "成片就绪",
  needs_human_review: "需人工复核",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = [
    "active",
    "completed",
    "ready",
    "user_reported_published",
  ].includes(status)
    ? "success"
    : ["failed", "blocked", "paused_by_error"].includes(status)
      ? "danger"
      : [
            "awaiting_user_review",
            "awaiting_manual_publication",
            "paused_by_budget",
          ].includes(status)
        ? "warning"
        : "neutral";
  return <Badge tone={tone}>{statusLabels[status] ?? status}</Badge>;
}
