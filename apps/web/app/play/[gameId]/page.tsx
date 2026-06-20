import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type PlayPageProps = {
  params: Promise<{
    gameId: string;
  }>;
};

export default async function PlayPage({ params }: PlayPageProps) {
  const user = await getCurrentUser();
  const { gameId } = await params;

  const game = await prisma.game.findFirst({
    where: {
      id: gameId,
      OR: [{ status: "PUBLISHED" }, ...(user ? [{ authorId: user.id }] : [])],
    },
    select: {
      id: true,
      title: true,
      description: true,
      tags: true,
      status: true,
      latestVersion: {
        select: {
          id: true,
          version: true,
          manifestUrl: true,
          entryUrl: true,
          artifactBaseUrl: true,
          entryFile: true,
          runtime: true,
        },
      },
      versions: {
        orderBy: { version: "desc" },
        take: 1,
        select: {
          id: true,
          version: true,
          manifestUrl: true,
          entryUrl: true,
          artifactBaseUrl: true,
          entryFile: true,
          runtime: true,
        },
      },
    },
  });

  if (!game) {
    notFound();
  }

  const version = game.latestVersion ?? game.versions[0];
  const entryUrl = version?.entryUrl ??
    (version ? `${version.artifactBaseUrl.replace(/\/$/, "")}/${version.entryFile}` : null);

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="text-sm text-zinc-400 transition hover:text-white">
          ← 返回首页
        </Link>
        <Link
          href={`/api/v1/games/${game.id}/play-meta`}
          className="text-sm text-indigo-300 transition hover:text-indigo-100"
        >
          查看 play-meta JSON
        </Link>
      </div>

      <section className="mx-auto mt-12 grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/20">
          <p className="text-sm text-indigo-300">{game.status}</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">{game.title}</h1>
          <p className="mt-4 text-sm leading-6 text-zinc-400">{game.description}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            {game.tags.map((tag) => (
              <span key={tag} className="rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-300">
                {tag}
              </span>
            ))}
          </div>

          <div className="mt-8 space-y-4 rounded-2xl border border-white/10 bg-zinc-900 p-4 text-xs leading-5 text-zinc-400">
            <p className="text-sm font-medium text-zinc-200">V1.7 Play Meta 占位验收</p>
            {version ? (
              <>
                <p>versionId：{version.id}</p>
                <p>manifestUrl：{version.manifestUrl}</p>
                <p>entryUrl：{entryUrl}</p>
                <p>artifactBaseUrl：{version.artifactBaseUrl}</p>
                <p>runtime：{version.runtime}</p>
              </>
            ) : (
              <p>该游戏还没有版本产物。V1.7 可先发布草稿生成占位 manifest，V2 再接入 MinIO 真实文件。</p>
            )}
          </div>
        </aside>

        <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 shadow-2xl shadow-black/20">
          {entryUrl ? (
            <iframe
              src={entryUrl}
              sandbox="allow-scripts allow-pointer-lock"
              className="h-[620px] w-full rounded-2xl border border-white/10 bg-zinc-900"
              title={game.title}
            />
          ) : (
            <div className="flex h-[620px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/15 bg-zinc-900 text-center">
              <h2 className="text-2xl font-semibold">等待产物生成</h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-zinc-400">
                当前 V1.7 只要求展示游戏 meta 与 play-meta。V2 会接入对象存储并动态加载真实远端游戏文件。
              </p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
