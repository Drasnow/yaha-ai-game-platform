"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type User = {
  displayName: string | null;
  email: string;
};

const AVATAR_COLORS = [
  "bg-indigo-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-violet-500",
  "bg-teal-500",
  "bg-orange-500",
];

function getInitials(name: string | null, email: string): string {
  if (name) {
    return name.slice(0, 2);
  }
  const local = email.split("@")[0] ?? "";
  return local.slice(0, 2).toUpperCase();
}

function getAvatarColor(text: string): string {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function UserAvatarMenu({ user }: { user: User }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const initials = getInitials(user.displayName, user.email);
  const color = getAvatarColor(user.email);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-center rounded-full transition hover:ring-2 hover:ring-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        aria-label="用户菜单"
        aria-expanded={open}
      >
        <span
          className={`flex h-8 w-8 items-center justify-center rounded-full ${color} text-xs font-semibold text-white select-none`}
        >
          {initials}
        </span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-2 w-52 overflow-hidden rounded-2xl border border-white/10 bg-zinc-900 shadow-2xl shadow-black/60">
            <div className="border-b border-white/10 px-4 py-3">
              <p className="truncate text-sm font-medium text-white">
                {user.displayName ?? "未设置昵称"}
              </p>
              <p className="mt-0.5 truncate text-xs text-zinc-500">
                {user.email}
              </p>
            </div>
            <div className="p-2">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  void fetch("/api/v1/auth/logout", { method: "POST" });
                  router.push("/login");
                  router.refresh();
                }}
                className="block w-full px-3 py-2 text-left text-sm text-zinc-400 transition hover:bg-white/5 hover:text-white"
              >
                退出登录
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
