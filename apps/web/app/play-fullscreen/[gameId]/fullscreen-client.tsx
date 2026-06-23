"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type PlayMetaResponse = {
  game: {
    id: string;
    title: string;
  };
  playMeta: {
    versionId: string;
    entryUrl: string;
    artifactBaseUrl: string;
    runtime: string;
  };
};

type LoadState = "loading" | "ready" | "failed";

type FullscreenClientProps = {
  gameId: string;
  preview: boolean;
};

export function FullscreenClient({ gameId, preview }: FullscreenClientProps) {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [entryUrl, setEntryUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPlayMeta() {
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
        setEntryUrl(data.playMeta.entryUrl);
        setLoadState("ready");
      } catch (error) {
        if (controller.signal.aborted) return;

        const message = error instanceof Error ? error.message : "加载游戏失败";
        setErrorMessage(message);
        setLoadState("failed");
      }
    }

    loadPlayMeta();

    return () => controller.abort();
  }, [gameId, preview]);

  return (
    <div className="fixed inset-0 flex flex-col bg-black">
      {/* Top bar */}
      <div className="flex items-center justify-between bg-zinc-900 px-4 py-2 text-sm text-zinc-400">
        <span className="truncate">{loadState === "ready" ? "全屏游玩模式" : "加载中..."}</span>
        <a
          href="/"
          className="ml-4 shrink-0 rounded bg-zinc-800 px-3 py-1 text-white transition hover:bg-zinc-700"
        >
          退出全屏
        </a>
      </div>

      {/* iframe fills remaining space */}
      <div className="relative flex-1">
        {loadState === "loading" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black text-white">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-200 border-t-transparent" />
            <p className="mt-4 text-sm text-zinc-400">正在加载游戏...</p>
          </div>
        )}

        {loadState === "failed" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black text-white">
            <h2 className="text-xl font-semibold text-red-300">加载失败</h2>
            <p className="mt-2 max-w-md text-center text-sm text-zinc-400">
              {errorMessage ?? "无法加载游戏文件"}
            </p>
            <a
              href="/"
              className="mt-6 rounded bg-zinc-800 px-4 py-2 text-sm text-white transition hover:bg-zinc-700"
            >
              返回首页
            </a>
          </div>
        )}

        {entryUrl && loadState === "ready" && (
          <iframe
            key={entryUrl}
            src={entryUrl}
            sandbox="allow-scripts allow-pointer-lock allow-forms allow-same-origin"
            className="h-full w-full border-0"
            title="game-fullscreen"
          />
        )}
      </div>
    </div>
  );
}
