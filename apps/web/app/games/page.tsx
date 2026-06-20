import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

function formatDate(date: Date) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default async function GamesPage() {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  const games = await prisma.game.findMany({
    where: { authorId: user.id },
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      title: true,
      description: true,
      tags: true,
      status: true,
      playCount: true,
      createdAt: true,
      updatedAt: true,
    },
  });

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="text-sm text-zinc-400 transition hover:text-white">
          ← 返回首页
        </Link>
        <LogoutButton />
      </div>

      <section className="mx-auto mt-14 max-w-6xl">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm text-indigo-300">已登录：{user.displayName ?? user.email}</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-6xl">
              我的游戏
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-300">
              查看你创建过的游戏草稿。后续会在这里进入编辑、生成和发布流程。
            </p>
          </div>
          <Link
            href="/create"
            className="rounded-full bg-indigo-500 px-6 py-3 text-center font-medium text-white transition hover:bg-indigo-400"
          >
            新建游戏
          </Link>
        </div>

        {games.length === 0 ? (
          <div className="mt-12 rounded-3xl border border-dashed border-white/15 bg-white/[0.04] p-10 text-center">
            <h2 className="text-2xl font-semibold">还没有游戏草稿</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              先创建一个游戏，保存标题、简介和玩法类型。
            </p>
            <Link
              href="/create"
              className="mt-6 inline-flex rounded-full bg-indigo-500 px-6 py-3 font-medium text-white transition hover:bg-indigo-400"
            >
              创建第一个游戏
            </Link>
          </div>
        ) : (
          <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {games.map((game) => (
              <article
                key={game.id}
                className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/20"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200">
                    {game.status}
                  </span>
                  <span className="text-xs text-zinc-500">游玩 {game.playCount}</span>
                </div>

                <h2 className="mt-5 line-clamp-2 text-2xl font-semibold tracking-tight">
                  {game.title}
                </h2>
                <p className="mt-3 line-clamp-3 text-sm leading-6 text-zinc-400">
                  {game.description}
                </p>

                <div className="mt-5 flex flex-wrap gap-2">
                  {game.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-300"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-6 border-t border-white/10 pt-4 text-xs leading-5 text-zinc-500">
                  <p>ID：{game.id}</p>
                  <p>创建：{formatDate(game.createdAt)}</p>
                  <p>更新：{formatDate(game.updatedAt)}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
