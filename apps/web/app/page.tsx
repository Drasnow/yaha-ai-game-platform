import Link from "next/link";

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
      <section className="mx-auto mt-8 max-w-6xl">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">
            发现由 AI 驱动的互动小游戏
          </h1>
          <p className="mt-6 text-lg leading-8 text-zinc-300">
            每天都有创作者通过自然语言和 AI Agent 生成新的互动游戏。探索、游玩，或用你自己的创意生成独一无二的作品。
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
