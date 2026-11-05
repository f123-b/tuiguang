"use client";
import { Badge, Button, Card } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  FileText,
  Layers,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api, post } from "../../lib/api";

import { Field } from "../page-shared";
export function Auth({ onComplete }: { onComplete: () => Promise<void> }) {
  const [register, setRegister] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <main className="auth-page">
      <div className="auth-story">
        <Link href="/dashboard" className="logo">
          <div className="logo-mark">
            <Layers size={25} />
          </div>
          <span>
            叙流<small>AI CREATOR</small>
          </span>
        </Link>
        <span className="eyebrow mint">A CONTINUOUS CREATIVE PARTNER</span>
        <h1>
          好产品的故事，
          <br />
          值得持续讲述。
        </h1>
        <p>
          让创作有节奏，让表达有依据。
          <br />
          AI 准备内容，你决定如何分享。
        </p>
        <div className="auth-steps">
          <span>
            <FileText size={17} />
            真实品牌
          </span>
          <i />
          <span>
            <Sparkles size={17} />
            持续创作
          </span>
          <i />
          <span>
            <ArrowDownToLine size={17} />
            亲自分享
          </span>
        </div>
        <small>本地开发版 · 无需提供社媒账号凭据</small>
      </div>
      <div className="auth-form-wrap">
        <Card>
          <Badge tone="blue">叙流 · 0.2.0 开发版</Badge>
          <h2>{register ? "建立你的创作空间" : "欢迎回到创作空间"}</h2>
          <p>
            {register
              ? "从你的第一个真实产品故事开始。"
              : "继续准备下一份值得分享的内容。"}
          </p>
          <form
            className="form-stack"
            onSubmit={async (e: FormEvent<HTMLFormElement>) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              const data = new FormData(e.currentTarget);
              try {
                await api(
                  register ? "/auth/register" : "/auth/login",
                  post({
                    email: data.get("email"),
                    password: data.get("password"),
                    ...(register ? { name: data.get("name") } : {}),
                  }),
                );
                await onComplete();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {register && (
              <Field label="工作区名称">
                <input
                  name="name"
                  autoComplete="organization"
                  maxLength={100}
                  required
                  placeholder="你的工作区"
                />
              </Field>
            )}
            <Field label="邮箱">
              <input
                name="email"
                type="email"
                autoComplete="username"
                required
                placeholder="you@example.com"
              />
            </Field>
            <Field label="密码">
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={10}
                maxLength={128}
                required
                placeholder="至少 10 个字符"
              />
            </Field>
            {error && (
              <div className="alert danger" role="alert">
                {error}
              </div>
            )}
            <Button type="submit" disabled={busy}>
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : register ? (
                "创建工作区"
              ) : (
                "登录"
              )}
              <ArrowRight size={16} />
            </Button>
          </form>
          <button
            className="auth-toggle"
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register ? "已有工作区？登录" : "还没有账号？创建工作区"}
          </button>
          <p className="auth-footnote">
            <ShieldCheck size={14} />
            平台最终发布由你亲自完成
          </p>
        </Card>
      </div>
    </main>
  );
}
