import Link from "next/link";
import { redirect } from "next/navigation";

import { CreateGameForm } from "@/components/create-game-form";
import { getCurrentUser } from "@/lib/auth";

export default async function CreatePage({
  searchParams,
}: {
  searchParams: Promise<{ gameId?: string; title?: string; description?: string }>;
}) {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  const { gameId, title, description } = await searchParams;

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <section className="mx-auto mt-14 max-w-6xl">
        <div className="max-w-3xl">
          {/* <p className="text-sm text-indigo-300">已登录：{user.displayName ?? user.email}</p> */}
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-6xl">
            {gameId ? "重新生成游戏" : "AI 生成互动游戏"}
          </h1>
          <p className="mt-6 text-lg leading-8 text-zinc-300">
            {gameId
              ? "基于已有游戏重新生成新版本，输入新的创意描述来调整游戏内容。"
              : "输入游戏创意并选择素材，触发 FastAPI Agent 生成任务；页面会展示任务进度、Agent 日志、预览入口和发布操作。"}
          </p>
          {gameId && (
            <Link
              href="/create"
              className="mt-3 inline-block text-sm text-indigo-300 underline hover:text-indigo-200"
            >
              取消重新生成，创建新游戏 →
            </Link>
          )}
        </div>

        <div className="mt-10">
          <CreateGameForm sourceGameId={gameId} prefillTitle={title} prefillDescription={description} />
        </div>
      </section>
    </main>
  );
}
