"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type CreatedGame = {
  id: string;
  title: string;
  description: string;
  tags: string[];
  status: string;
  createdAt: string;
};

const gameplayOptions = [
  {
    value: "quiz",
    label: "问答闯关",
    description: "适合知识问答、课堂互动、选择题挑战。",
  },
  {
    value: "story",
    label: "剧情选择",
    description: "适合分支剧情、角色扮演、文字冒险。",
  },
  {
    value: "puzzle",
    label: "解谜挑战",
    description: "适合逻辑谜题、找线索、关卡推理。",
  },
  {
    value: "simulation",
    label: "经营模拟",
    description: "适合养成、资源管理、策略经营原型。",
  },
];

export function CreateGameForm() {
  const [error, setError] = useState<string | null>(null);
  const [createdGame, setCreatedGame] = useState<CreatedGame | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);

    setError(null);
    setCreatedGame(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/games", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: String(formData.get("title") ?? ""),
          description: String(formData.get("description") ?? ""),
          gameplayType: String(formData.get("gameplayType") ?? ""),
        }),
      });

      const body = await response.json().catch(() => null);

      if (!response.ok) {
        setError(body?.error ?? "创建失败，请稍后重试");
        return;
      }

      form.reset();
      setCreatedGame(body.game);
    } catch {
      setError("网络异常，请稍后重试");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <form
        onSubmit={handleSubmit}
        className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 text-left shadow-2xl shadow-black/20 sm:p-8"
      >
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold">基础信息</h2>
          <p className="text-sm leading-6 text-zinc-400">
            先保存游戏草稿，后续 V1.8 会接入 AI 生成任务和版本产物。
          </p>
        </div>

        <div className="mt-8 space-y-6">
          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">游戏标题</span>
            <input
              name="title"
              required
              maxLength={80}
              className="w-full rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
              placeholder="例如：星际知识闯关"
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">游戏简介</span>
            <textarea
              name="description"
              required
              rows={5}
              maxLength={1000}
              className="w-full resize-none rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
              placeholder="简单描述玩家目标、核心玩法和游戏主题。"
            />
          </label>

          <fieldset className="space-y-3">
            <legend className="text-sm text-zinc-300">玩法类型</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {gameplayOptions.map((option) => (
                <label
                  key={option.value}
                  className="cursor-pointer rounded-2xl border border-white/10 bg-zinc-900 p-4 transition has-[:checked]:border-indigo-400 has-[:checked]:bg-indigo-500/10"
                >
                  <input
                    type="radio"
                    name="gameplayType"
                    value={option.value}
                    required
                    className="sr-only"
                  />
                  <span className="block font-medium text-white">{option.label}</span>
                  <span className="mt-1 block text-xs leading-5 text-zinc-400">
                    {option.description}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          {error ? (
            <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-indigo-500 px-4 py-3 font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "保存中..." : "保存游戏草稿"}
          </button>
        </div>
      </form>

      <aside className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 text-left sm:p-8">
        <h2 className="text-2xl font-semibold">创建结果</h2>
        {createdGame ? (
          <div className="mt-6 space-y-4 text-sm leading-6 text-zinc-300">
            <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-emerald-200">
              已保存到 games 表。
            </p>
            <div>
              <p className="text-zinc-500">游戏 ID</p>
              <p className="break-all font-mono text-xs text-zinc-200">{createdGame.id}</p>
            </div>
            <div>
              <p className="text-zinc-500">标题</p>
              <p className="text-zinc-100">{createdGame.title}</p>
            </div>
            <div>
              <p className="text-zinc-500">状态</p>
              <p className="text-zinc-100">{createdGame.status}</p>
            </div>
            <div>
              <p className="text-zinc-500">标签</p>
              <p className="text-zinc-100">{createdGame.tags.join(" / ")}</p>
            </div>
            <Link
              href="/games"
              className="inline-flex rounded-full bg-indigo-500 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-400"
            >
              查看我的游戏
            </Link>
          </div>
        ) : (
          <p className="mt-6 text-sm leading-6 text-zinc-400">
            提交左侧表单后，这里会显示数据库返回的游戏草稿信息。
          </p>
        )}
      </aside>
    </div>
  );
}
