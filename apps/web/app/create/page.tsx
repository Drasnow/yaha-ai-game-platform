import Link from "next/link";
import { redirect } from "next/navigation";

import { CreateGameForm } from "@/components/create-game-form";
import { LogoutButton } from "@/components/logout-button";
import { getCurrentUser } from "@/lib/auth";

export default async function CreatePage() {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="text-sm text-zinc-400 transition hover:text-white">
          ← 返回首页
        </Link>
        <LogoutButton />
      </div>

      <section className="mx-auto mt-14 max-w-6xl">
        <div className="max-w-3xl">
          <p className="text-sm text-indigo-300">已登录：{user.displayName ?? user.email}</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-6xl">
            创建游戏草稿
          </h1>
          <p className="mt-6 text-lg leading-8 text-zinc-300">
            填写标题、简介和玩法类型，先把游戏基础信息保存到 games 表。
          </p>
        </div>

        <div className="mt-10">
          <CreateGameForm />
        </div>
      </section>
    </main>
  );
}
