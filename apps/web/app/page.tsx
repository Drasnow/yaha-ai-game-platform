import Link from "next/link";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

function formatDate(date: Date | null) {
  if (!date) {
    return "未发布";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

export default async function Home() {
  const user = await getCurrentUser();
  const games = await prisma.game.findMany({
    where: { status: "PUBLISHED" },
    orderBy: { publishedAt: "desc" },
    select: {
      id: true,
      title: true,
      description: true,
      coverUrl: true,
      tags: true,
      playCount: true,
      publishedAt: true,
      author: {
        select: {
          displayName: true,
          email: true,
        },
      },
    },
  });

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="font-semibold tracking-tight">
          Yaha AI Game Platform
        </Link>
        <div className="flex items-center gap-3 text-sm">
          {user ? (
            <>
              <Link href="/games" className="text-zinc-300 transition hover:text-white">
                我的游戏
              </Link>
              <Link
                href="/create"
                className="rounded-full bg-indigo-500 px-4 py-2 font-medium transition hover:bg-indigo-400"
              >
                新建游戏
              </Link>
            </>
          ) : (
            <>
              <Link href="/login" className="text-zinc-300 transition hover:text-white">
                登录
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-indigo-500 px-4 py-2 font-medium transition hover:bg-indigo-400"
              >
                免费注册
              </Link>
            </>
          )}
        </div>
      </nav>

      <section className="mx-auto mt-16 max-w-6xl">
        <div className="max-w-3xl">
          <p className="w-fit rounded-full border border-white/10 px-4 py-1 text-sm text-zinc-300">
            V1.8 · 数据库示例游戏
          </p>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight sm:text-6xl">
            浏览、发布和游玩 AI 互动小游戏
          </h1>
          <p className="mt-6 text-lg leading-8 text-zinc-300">
            首页展示数据库中 published 状态的游戏。点击卡片进入 Play 页面，读取后端 play-meta 展示远端产物地址。
          </p>
        </div>

        {games.length === 0 ? (
          <div className="mt-12 rounded-3xl border border-dashed border-white/15 bg-white/[0.04] p-10 text-center">
            <h2 className="text-2xl font-semibold">暂无已发布游戏</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              请先在 apps/web 下执行 pnpm prisma db seed 写入 V1.8 示例数据。
            </p>
          </div>
        ) : (
          <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {games.map((game) => (
              <Link
                key={game.id}
                href={`/play/${game.id}`}
                className="group overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] shadow-2xl shadow-black/20 transition hover:-translate-y-1 hover:border-indigo-300/50"
              >
                <div className="flex h-40 items-center justify-center bg-gradient-to-br from-indigo-500/30 via-fuchsia-500/20 to-cyan-500/20 text-5xl">
                  {game.coverUrl ? "🎮" : "✨"}
                </div>
                <div className="p-6">
                  <div className="flex items-center justify-between gap-3 text-xs text-zinc-500">
                    <span>{formatDate(game.publishedAt)}</span>
                    <span>游玩 {game.playCount}</span>
                  </div>
                  <h2 className="mt-4 line-clamp-2 text-2xl font-semibold tracking-tight group-hover:text-indigo-200">
                    {game.title}
                  </h2>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-zinc-400">
                    {game.description}
                  </p>
                  <p className="mt-4 text-sm text-zinc-300">
                    作者：{game.author.displayName ?? game.author.email}
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
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
