import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "叙流 · AI 持续创作者",
  description: "让产品的故事，持续发生。持续创作、人工发布、真实反馈。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
