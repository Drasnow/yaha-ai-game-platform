"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

type Game = {
  id: string;
  title: string;
  description: string;
  tags: string[];
  status: string;
  latestVersionId: string | null;
};

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String(payload.error)
        : `请求失败：${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

function EditModal({
  game,
  onClose,
}: {
  game: Game;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(game.title);
  const [description, setDescription] = useState(game.description);
  const [tags, setTags] = useState(game.tags.join(", "));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  async function handleSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await readJson<{ game: unknown }>(
        await fetch(`/api/v1/games/${game.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description, tags: tagList }),
        }),
      );
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="relative w-full max-w-lg rounded-3xl border border-white/15 bg-zinc-900 p-8 shadow-2xl shadow-black/80">
        <button
          onClick={onClose}
          className="absolute right-5 top-5 rounded-xl border border-white/10 px-3 py-1.5 text-sm text-zinc-400 transition hover:bg-white/10 hover:text-white"
        >
          ✕
        </button>

        <h2 className="text-xl font-semibold">编辑游戏信息</h2>
        <p className="mt-1 text-sm text-zinc-400">修改标题、简介和标签，保存后生效。</p>

        <form onSubmit={handleSave} className="mt-6 space-y-4">
          <label className="block space-y-1.5 text-sm">
            <span className="text-zinc-300">游戏名称</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={80}
              required
              className="w-full rounded-2xl border border-white/10 bg-zinc-800 px-4 py-3 text-white outline-none transition focus:border-indigo-400"
            />
          </label>

          <label className="block space-y-1.5 text-sm">
            <span className="text-zinc-300">游戏简介</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={4}
              required
              className="w-full resize-none rounded-2xl border border-white/10 bg-zinc-800 px-4 py-3 text-white outline-none transition focus:border-indigo-400"
            />
          </label>

          <label className="block space-y-1.5 text-sm">
            <span className="text-zinc-300">标签（逗号分隔）</span>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              maxLength={200}
              placeholder="射击, 街机, 怀旧"
              className="w-full rounded-2xl border border-white/10 bg-zinc-800 px-4 py-3 text-white outline-none transition focus:border-indigo-400"
            />
          </label>

          {error && (
            <p className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-2xl bg-indigo-500 px-4 py-3 font-medium text-white transition hover:bg-indigo-400 disabled:opacity-50"
            >
              {saving ? "保存中..." : "保存修改"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-2xl border border-white/10 bg-zinc-800 px-4 py-3 font-medium text-zinc-300 transition hover:bg-zinc-700"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function EditGameButton({ game }: { game: Game }) {
  const [modalOpen, setModalOpen] = useState(false);

  const regenerateHref = `/create?gameId=${game.id}&title=${encodeURIComponent(game.title)}&description=${encodeURIComponent(game.description)}`;

  return (
    <>
      {modalOpen && <EditModal game={game} onClose={() => setModalOpen(false)} />}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Link
          href={`/play/${game.id}${game.status === "DRAFT" ? "?preview=1" : ""}`}
          className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-400"
        >
          {game.status === "DRAFT" ? "预览草稿" : "游玩"}
        </Link>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-full border border-white/20 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-200 transition hover:bg-zinc-700"
        >
          编辑
        </button>
        <Link
          href={regenerateHref}
          className="rounded-full border border-indigo-400/40 bg-indigo-500/10 px-4 py-2 text-sm font-medium text-indigo-200 transition hover:bg-indigo-500/20"
        >
          重新生成
        </Link>
      </div>
    </>
  );
}
