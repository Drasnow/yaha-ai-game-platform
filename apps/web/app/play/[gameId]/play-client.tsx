"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

type PlayMetaResponse = {
  game: {
    id: string;
    title: string;
    description: string;
    coverUrl: string | null;
    tags: string[];
    status: string;
    isPreview: boolean;
    author: {
      id: string;
      displayName: string | null;
      email: string;
    };
  };
  playMeta: {
    versionId: string;
    version: number;
    manifestUrl: string;
    entryUrl: string;
    artifactBaseUrl: string;
    entryFile: string;
    runtime: string;
    createdAt: string;
  };
};

type LoadState = "loading-meta" | "loading-frame" | "ready" | "failed";
type PlayEventType = "load_start" | "load_success" | "load_failed" | "play_start";

type PlayClientProps = {
  gameId: string;
  preview: boolean;
};

export function PlayClient({ gameId, preview }: PlayClientProps) {
  const [playData, setPlayData] = useState<PlayMetaResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading-meta");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const playStartReportedRef = useRef(false);

  const reportPlayEvent = useCallback(
    async (eventType: PlayEventType, data?: PlayMetaResponse, message?: string) => {
      try {
        await fetch("/api/v1/play-events", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            gameId,
            versionId: data?.playMeta.versionId,
            eventType,
            message,
            metadata: data
              ? {
                  manifestUrl: data.playMeta.manifestUrl,
                  entryUrl: data.playMeta.entryUrl,
                  artifactBaseUrl: data.playMeta.artifactBaseUrl,
                  runtime: data.playMeta.runtime,
                }
              : undefined,
          }),
          keepalive: true,
        });
      } catch (error) {
        console.warn("Failed to report play event", error);
      }
    },
    [gameId],
  );

  useEffect(() => {
    const controller = new AbortController();

    async function loadPlayMeta() {
      setLoadState("loading-meta");
      setErrorMessage(null);
      playStartReportedRef.current = false;

      try {
        const query = preview ? "?preview=1" : "";
        const response = await fetch(`/api/v1/games/${gameId}/play-meta${query}`, {
          signal: controller.signal,
          cache: "no-store",
        });

        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { error?: string } | null;
          throw new Error(payload?.error ?? "加载游戏元信息失败");
        }

        const data = (await response.json()) as PlayMetaResponse;
        setPlayData(data);
        setLoadState("loading-frame");
        void reportPlayEvent("load_start", data, "Play 页面已读取 play-meta，开始加载远端 iframe");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        const message = error instanceof Error ? error.message : "加载游戏失败";
        setLoadState("failed");
        setErrorMessage(message);
        void reportPlayEvent("load_failed", undefined, message);
      }
    }

    loadPlayMeta();

    return () => controller.abort();
  }, [gameId, preview, reportPlayEvent]);

  const isLoading = loadState === "loading-meta" || loadState === "loading-frame";

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="text-sm text-zinc-400 transition hover:text-white">
          ← 返回首页
        </Link>
        <Link
          href={`/api/v1/games/${gameId}/play-meta${preview ? "?preview=1" : ""}`}
          className="text-sm text-indigo-300 transition hover:text-indigo-100"
        >
          查看 play-meta JSON
        </Link>
      </div>

      <section className="mx-auto mt-12 grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/20">
          <p className="text-sm text-indigo-300">
            {playData?.game.isPreview ? "PREVIEW · DRAFT" : playData?.game.status ?? "LOADING"}
          </p>
          {playData?.game.isPreview ? (
            <p className="mt-3 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              当前为草稿预览，仅作者可访问；发布后才会进入首页列表。
            </p>
          ) : null}
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">
            {playData?.game.title ?? "正在加载游戏"}
          </h1>
          <p className="mt-4 text-sm leading-6 text-zinc-400">
            {playData?.game.description ?? "正在从 play-meta API 读取远端游戏产物信息。"}
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {(playData?.game.tags ?? ["remote", "iframe", "minio"]).map((tag) => (
              <span key={tag} className="rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-300">
                {tag}
              </span>
            ))}
          </div>

          <div className="mt-8 space-y-4 rounded-2xl border border-white/10 bg-zinc-900 p-4 text-xs leading-5 text-zinc-400">
            <p className="text-sm font-medium text-zinc-200">V2.7 Play 动态加载与事件埋点</p>
            {playData ? (
              <>
                <p>versionId：{playData.playMeta.versionId}</p>
                <p>manifestUrl：{playData.playMeta.manifestUrl}</p>
                <p>entryUrl：{playData.playMeta.entryUrl}</p>
                <p>artifactBaseUrl：{playData.playMeta.artifactBaseUrl}</p>
                <p>runtime：{playData.playMeta.runtime}</p>
              </>
            ) : (
              <p>页面会先请求 `/api/v1/games/{gameId}/play-meta`，再用返回的 entryUrl 加载 iframe。</p>
            )}
          </div>
        </aside>

        <section className="relative rounded-3xl border border-white/10 bg-white/[0.04] p-4 shadow-2xl shadow-black/20">
          {isLoading ? (
            <div className="absolute inset-4 z-10 flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-zinc-950/90 text-center backdrop-blur">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-200 border-t-transparent" />
              <h2 className="mt-5 text-2xl font-semibold">
                {loadState === "loading-meta" ? "正在读取 play-meta" : "正在加载远端游戏"}
              </h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-zinc-400">
                游戏文件来自 MinIO 对象存储，页面不会运行本地写死组件。
              </p>
            </div>
          ) : null}

          {loadState === "failed" ? (
            <div className="flex h-[720px] flex-col items-center justify-center rounded-2xl border border-dashed border-red-400/30 bg-red-950/20 text-center">
              <h2 className="text-2xl font-semibold text-red-100">游戏加载失败</h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-red-100/70">
                {errorMessage ?? "请确认游戏版本已发布，并且 MinIO 远端产物可公开读取。"}
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-6 rounded-full bg-red-500 px-5 py-2 text-sm font-medium text-white transition hover:bg-red-400"
              >
                重新加载
              </button>
            </div>
          ) : playData ? (
            <iframe
              src={playData.playMeta.entryUrl}
              sandbox="allow-scripts allow-pointer-lock"
              className="h-[720px] w-full rounded-2xl border border-white/10 bg-zinc-900"
              title={playData.game.title}
              onLoad={() => {
                setLoadState("ready");
                void reportPlayEvent("load_success", playData, "远端 iframe 加载成功");
                if (!playStartReportedRef.current) {
                  playStartReportedRef.current = true;
                  void reportPlayEvent("play_start", playData, "玩家进入可交互游戏画面");
                }
              }}
              onError={() => {
                const message = "远端 iframe 加载失败";
                setLoadState("failed");
                setErrorMessage(message);
                void reportPlayEvent("load_failed", playData, message);
              }}
            />
          ) : null}
        </section>
      </section>
    </main>
  );
}