import Link from "next/link";
import { getCurrentUser } from "@/lib/auth";
import { UserAvatarMenu } from "@/components/user-avatar-menu";

export async function SiteHeader() {
  const user = await getCurrentUser();

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#09090b] backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link
          href="/"
          className="text-lg font-semibold text-white tracking-tight transition hover:text-indigo-300"
        >
          首页
        </Link>

        <div className="flex items-center gap-4 text-sm">
          {user ? (
            <>
              <Link
                href="/games"
                className="text-zinc-300 transition hover:text-white"
              >
                我的游戏
              </Link>
              <UserAvatarMenu user={user} />
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-zinc-300 transition hover:text-white"
              >
                登录
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-indigo-500 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-400"
              >
                免费注册
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
