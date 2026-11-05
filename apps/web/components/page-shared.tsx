import type { ReactNode } from "react";
import type { Store } from "../lib/api";
export const platformName: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  bilibili: "哔哩哔哩",
};
export const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
export const dateText = (value: string) =>
  new Date(value).toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour12: false,
  });

export type Action = (
  fn: () => Promise<unknown>,
  success?: string,
) => Promise<void>;
export type PageProps = {
  store: Store;
  action: Action;
  busy: boolean;
  path: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
