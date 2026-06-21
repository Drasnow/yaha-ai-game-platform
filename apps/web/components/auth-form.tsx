"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type AuthMode = "login" | "register";

type AuthFormProps = {
  mode: AuthMode;
};

const copy = {
  login: {
    title: "登录 Yaha",
    description: "继续创建和管理你的 AI 互动小游戏。",
    button: "登录",
    loading: "登录中...",
    switchText: "还没有账号？",
    switchHref: "/register",
    switchLabel: "去注册",
    endpoint: "/api/v1/auth/login",
  },
  register: {
    title: "注册 Yaha",
    description: "创建账号，开始生成你的第一个互动小游戏。",
    button: "注册并登录",
    loading: "注册中...",
    switchText: "已经有账号？",
    switchHref: "/login",
    switchLabel: "去登录",
    endpoint: "/api/v1/auth/register",
  },
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const text = copy[mode];
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const payload: Record<string, string> = {
      email: String(formData.get("email") ?? ""),
      password: String(formData.get("password") ?? ""),
    };

    if (mode === "register") {
      payload.displayName = String(formData.get("displayName") ?? "");
    }

    const response = await fetch(text.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      setError(body?.error ?? "请求失败，请稍后重试");
      setIsSubmitting(false);
      return;
    }

    router.push("/games");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 py-12 text-white">
      <section className="w-full max-w-md rounded-3xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl shadow-black/30">
        <Link href="/" className="text-sm text-zinc-400 transition hover:text-white">
          ← 返回首页
        </Link>
        <div className="mt-8 space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">{text.title}</h1>
          <p className="text-sm leading-6 text-zinc-400">{text.description}</p>
        </div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <label className="block space-y-2 text-sm">
              <span className="text-zinc-300">展示名</span>
              <input
                name="displayName"
                type="text"
                autoComplete="name"
                className="w-full rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
                placeholder="例如：雷博"
              />
            </label>
          ) : null}

          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">邮箱</span>
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              className="w-full rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
              placeholder="you@example.com"
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">密码</span>
            <input
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? 8 : 1}
              className="w-full rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
              placeholder={mode === "register" ? "至少 8 位" : "输入密码"}
            />
          </label>

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
            {isSubmitting ? text.loading : text.button}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-400">
          {text.switchText} {" "}
          <Link href={text.switchHref} className="font-medium text-indigo-300 hover:text-indigo-200">
            {text.switchLabel}
          </Link>
        </p>
      </section>
    </main>
  );
}
