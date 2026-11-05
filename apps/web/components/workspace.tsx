"use client";

import { Badge, Button, Card, EmptyState } from "@xuliu/ui";
import {
  ArrowDownToLine,
  ArrowRight,
  Bell,
  CalendarDays,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clapperboard,
  ExternalLink,
  FolderOpen,
  Gauge,
  Layers,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  Moon,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sprout,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  post,
  type Analytics,
  type Asset,
  type Brand,
  type Content,
  type Creator,
  type Dashboard,
  type Handoff,
  type Publication,
  type Run,
  type Store,
  type Video,
} from "../lib/api";

import { PageHeader, type Action, type PageProps } from "./page-shared";
import { AnalyticsPage } from "./pages/analytics";
import { AssetsPage } from "./pages/assets";
import { Auth } from "./pages/auth";
import { BrandPage } from "./pages/brand";
import { ArticlePage, ContentLibrary } from "./pages/content";
import { ActivityPage, CalendarPage, CreatorPage } from "./pages/creator";
import { GrowthPage } from "./pages/growth";
import { HelpPage } from "./pages/help";
import { Overview } from "./pages/overview";
import { PublishPage } from "./pages/publish";
import { OpsPage, SettingsPage } from "./pages/settings";
import { VideoPage } from "./pages/video";

const groups = [
  {
    label: "工作空间",
    items: [
      { href: "/dashboard", label: "运营总览", icon: LayoutDashboard },
      { href: "/creator", label: "我的 AI 创作者", icon: Sparkles },
      { href: "/calendar", label: "选题与日历", icon: CalendarDays },
    ],
  },
  {
    label: "内容生产",
    items: [
      { href: "/campaigns", label: "内容工作室", icon: Layers },
      { href: "/studio/video/new", label: "AI 宣传视频", icon: Clapperboard },
      { href: "/publish", label: "人工发布中心", icon: ArrowDownToLine },
    ],
  },
  {
    label: "运营与成长",
    items: [
      { href: "/analytics", label: "数据与洞察", icon: Gauge },
      { href: "/growth", label: "成长与记忆", icon: Sprout },
      { href: "/brand", label: "品牌与素材", icon: FolderOpen },
    ],
  },
];
export default function Workspace({ path }: { path: string }) {
  const router = useRouter();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [light, setLight] = useState(false);
  const [themeReady, setThemeReady] = useState(false);
  const [loginRequired, setLoginRequired] = useState(path === "/auth/login");

  useEffect(() => {
    if (store && path === "/auth/login") router.replace("/dashboard");
  }, [store, path, router]);

  const refresh = useCallback(async () => {
    const [
      user,
      brands,
      creators,
      contents,
      runs,
      assets,
      videos,
      handoffs,
      publications,
      analytics,
      dashboard,
    ] = await Promise.all([
      api<Store["user"]>("/auth/me"),
      api<Brand[]>("/brands"),
      api<Creator[]>("/creators"),
      api<Content[]>("/content/packages"),
      api<Run[]>("/creator-runs"),
      api<Asset[]>("/assets"),
      api<Video[]>("/videos/projects"),
      api<Handoff[]>("/manual-publication/packages"),
      api<Publication[]>("/manual-publication/records"),
      api<Analytics>("/analytics"),
      api<Dashboard>("/dashboard"),
    ]);
    setStore({
      user,
      brands,
      creators,
      contents,
      runs,
      assets,
      videos,
      handoffs,
      publications,
      analytics,
      dashboard,
    });
    setLoginRequired(false);
  }, []);

  const reportError = useCallback((e: unknown) => {
    const problem = e as Error & { status?: number; trace?: string };
    if (problem.status === 401) {
      setLoginRequired(true);
      return;
    }
    setError(
      `${problem.message || "操作未完成"}${problem.trace ? ` · 诊断编号 ${problem.trace}` : ""}`,
    );
  }, []);

  useEffect(() => {
    refresh()
      .catch(reportError)
      .finally(() => setLoading(false));
  }, [refresh, reportError]);
  useEffect(() => {
    setMobileNav(false);
    setError("");
  }, [path]);
  useEffect(() => {
    if (!themeReady) return;
    document.documentElement.dataset.theme = light ? "light" : "dark";
    localStorage.setItem("creator-theme", light ? "light" : "dark");
  }, [light, themeReady]);
  useEffect(() => {
    setLight(localStorage.getItem("creator-theme") === "light");
    setThemeReady(true);
  }, []);
  useEffect(() => {
    if (
      !store ||
      ![...store.runs, ...store.videos].some((r) =>
        ["queued", "running"].includes(r.status),
      )
    )
      return;
    const timer = setInterval(() => {
      refresh().catch(reportError);
    }, 5000);
    return () => clearInterval(timer);
  }, [store, refresh, reportError]);

  const action: Action = async (fn, success = "已保存") => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      await refresh();
      setNotice(success);
    } catch (e) {
      reportError(e);
    } finally {
      setBusy(false);
    }
  };

  if (loginRequired)
    return (
      <Auth
        onComplete={async () => {
          await refresh();
          router.push("/dashboard");
        }}
      />
    );
  const pageTitle = titleFor(path);
  const creator = store?.creators[0];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        跳至主要内容
      </a>
      {mobileNav && (
        <button
          className="nav-backdrop"
          aria-label="关闭导航"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <Link href="/dashboard" className="logo">
          <div className="logo-mark">
            <Layers size={23} />
          </div>
          <span>
            叙流<small>AI CREATOR</small>
          </span>
          <Badge tone="blue">DEV</Badge>
        </Link>
        <div className="workspace-switch">
          <span className="brand-avatar">
            {store?.brands[0]?.name?.[0] || "叙"}
          </span>
          <span>
            {store?.brands[0]?.name || "我的工作空间"}
            <small>独立创作者工作区</small>
          </span>
          <ChevronDown size={14} />
        </div>
        <nav aria-label="主导航">
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => {
                const selected =
                  item.href === path ||
                  (item.href === "/studio/video/new" &&
                    path.startsWith("/studio/video")) ||
                  (item.href === "/campaigns" &&
                    path.startsWith("/studio/article"));
                return (
                  <Link
                    className={`nav-item ${selected ? "selected" : ""}`}
                    aria-current={selected ? "page" : undefined}
                    href={item.href}
                    key={item.href}
                  >
                    <item.icon size={18} />
                    <span>{item.label}</span>
                    {item.href === "/publish" &&
                      !!store?.dashboard.counts.awaiting_manual && (
                        <b>{store.dashboard.counts.awaiting_manual}</b>
                      )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="creator-mini">
            <span
              className={`live-dot ${creator?.status === "active" ? "active" : ""}`}
            />
            <span>
              {creator ? creator.name : "还没有创作者"}
              <small>
                {creator
                  ? creator.status === "active"
                    ? "持续准备，等你审阅"
                    : "任务制作已暂停"
                  : "创建你的第一位内容伙伴"}
              </small>
            </span>
          </div>
          <Link href="/help" className="nav-item">
            <CircleHelp size={18} />
            <span>帮助与使用指南</span>
            <ExternalLink size={13} />
          </Link>
          <Link href="/settings" className="nav-item">
            <Settings2 size={18} />
            <span>设置</span>
          </Link>
          <button
            className="profile"
            onClick={() =>
              action(async () => {
                await api("/auth/logout", post());
                setLoginRequired(true);
              }, "已退出")
            }
          >
            <span className="avatar">{store?.user.name[0] || "我"}</span>
            <span>
              {store?.user.name || "正在加载"}
              <small>本地开发版 · 0.1.0</small>
            </span>
            <LogOut size={15} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu"
              aria-label="展开导航"
              onClick={() => setMobileNav(true)}
            >
              <Menu size={20} />
            </button>
            <span>工作空间</span>
            <ChevronRight size={13} />
            <strong>{pageTitle}</strong>
          </div>
          <div className="top-actions">
            <div className="search">
              <Search size={15} />
              <input
                aria-label="搜索页面和功能"
                placeholder="搜索页面和功能…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <kbd>⌕</kbd>
              {search && (
                <div className="search-results">
                  {groups
                    .flatMap((g) => g.items)
                    .filter((i) => i.label.includes(search))
                    .map((i) => (
                      <Link
                        key={i.href}
                        href={i.href}
                        onClick={() => setSearch("")}
                      >
                        {i.label}
                        <ArrowRight size={14} />
                      </Link>
                    ))}
                </div>
              )}
            </div>
            <button
              className="icon-button"
              aria-label="切换深浅主题"
              onClick={() => setLight(!light)}
            >
              {light ? <Moon size={17} /> : <Sun size={17} />}
            </button>
            <Link
              className="icon-button"
              aria-label="查看任务通知"
              href="/creator/activity"
            >
              <Bell size={18} />
              {store?.runs.some((r) => r.status === "failed") && <i />}
            </Link>
            <Link className="button primary small" href="/campaigns">
              <Plus size={16} />
              新建内容
            </Link>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {error && (
            <div className="alert danger" role="alert">
              <span>{error}</span>
              <button aria-label="关闭错误" onClick={() => setError("")}>
                <X size={17} />
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <CheckCheck size={17} />
              {notice}
              <button onClick={() => setNotice("")} aria-label="关闭提示">
                <X size={15} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading">
              <LoaderCircle className="spin" size={24} />
              <p>正在读取你的工作空间…</p>
            </div>
          ) : !store ? (
            <EmptyState
              title="暂时无法连接工作区"
              description="请确认 API 服务已启动。"
              action={
                <Button onClick={() => action(refresh, "已重新连接")}>
                  重新连接
                </Button>
              }
            />
          ) : (
            <PageContent
              store={store}
              path={path}
              busy={busy}
              action={action}
            />
          )}
        </main>
        <footer className="page-footer">
          <span>
            <ShieldCheck size={13} />
            AI 持续创作，用户自行发布
          </span>
          <span>本地开发版 · 数据保存在你的工作区</span>
        </footer>
      </div>
      <nav className="mobile-tabs" aria-label="移动导航">
        {[
          ["/dashboard", "总览", LayoutDashboard],
          ["/calendar", "日历", CalendarDays],
          ["/campaigns", "创作", Plus],
          ["/publish", "发布", ArrowDownToLine],
          ["/settings", "我的", UserRound],
        ].map(([href, label, Icon]) => (
          <Link
            key={href as string}
            href={href as string}
            className={path === href ? "selected" : ""}
          >
            {typeof Icon !== "string" && <Icon size={20} />}
            <span>{label as string}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

function titleFor(path: string) {
  if (path.startsWith("/studio/video")) return "AI 宣传视频";
  if (path.startsWith("/studio/article")) return "图文编辑器";
  if (path.startsWith("/publish")) return "人工发布中心";
  if (path.startsWith("/analytics")) return "数据与洞察";
  if (path.startsWith("/onboarding")) return "首次设置";
  if (path.startsWith("/creator")) return "我的 AI 创作者";
  if (path.startsWith("/ops")) return "诊断与维护";
  return (
    (
      {
        "/dashboard": "运营总览",
        "/campaigns": "内容工作室",
        "/calendar": "选题与日历",
        "/topics": "选题池",
        "/growth": "成长与记忆",
        "/brand": "品牌与素材",
        "/settings": "设置",
        "/help": "帮助中心",
        "/compliance": "合规待办",
        "/studio/assets": "素材库",
        "/studio/covers": "封面模板",
      } as Record<string, string>
    )[path] || "工作空间"
  );
}

function PageContent(props: PageProps) {
  const { path } = props;
  if (path === "/dashboard" || path === "/") return <Overview {...props} />;
  if (path === "/brand" || path === "/onboarding/brand")
    return <BrandPage {...props} />;
  if (path === "/studio/assets") return <AssetsPage {...props} />;
  if (path.startsWith("/creator") || path === "/onboarding/creator")
    return path.endsWith("activity") ? (
      <ActivityPage {...props} />
    ) : (
      <CreatorPage {...props} />
    );
  if (
    ["/calendar", "/topics", "/onboarding/preview"].includes(path) ||
    path.startsWith("/topics/")
  )
    return <CalendarPage {...props} />;
  if (path.startsWith("/studio/article/")) return <ArticlePage {...props} />;
  if (path === "/campaigns" || path.startsWith("/compliance"))
    return <ContentLibrary {...props} />;
  if (path.startsWith("/studio/video")) return <VideoPage {...props} />;
  if (path.startsWith("/publish")) return <PublishPage {...props} />;
  if (path.startsWith("/analytics")) return <AnalyticsPage {...props} />;
  if (path.startsWith("/growth")) return <GrowthPage {...props} />;
  if (path.startsWith("/ops")) return <OpsPage {...props} />;
  if (path === "/settings") return <SettingsPage {...props} />;
  if (path === "/help" || path === "/onboarding/welcome") return <HelpPage />;
  if (path === "/studio/covers")
    return (
      <>
        <PageHeader
          title="封面模板"
          description="当前版本提供一款可实际导出的产品笔记封面。"
        />
        <Card>
          <div className="template-sample">
            <span>产品创作笔记</span>
            <h2>
              让产品的故事
              <br />
              被更多人看见
            </h2>
            <p>标题与品牌来自你的内容，准备发布包时生成 1080 × 1440 PNG。</p>
          </div>
          <Link className="button primary" href="/campaigns">
            选择内容，生成封面
          </Link>
        </Card>
      </>
    );
  return (
    <EmptyState
      title="页面不存在"
      description="请通过侧栏打开工作区功能。"
      action={
        <Link href="/dashboard" className="button primary">
          返回总览
        </Link>
      }
    />
  );
}
