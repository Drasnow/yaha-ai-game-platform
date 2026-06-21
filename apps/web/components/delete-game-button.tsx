"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type DeleteGameButtonProps = {
  gameId: string;
  gameTitle: string;
};

export function DeleteGameButton({ gameId, gameTitle }: DeleteGameButtonProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setErrorMessage(null);

    try {
      const response = await fetch(`/api/v1/games/${gameId}`, { method: "DELETE" });
      const payload = (await response.json().catch(() => null)) as { error?: string } | null;

      if (!response.ok) {
        throw new Error(payload?.error ?? "删除失败");
      }

      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "删除失败");
      setDeleting(false);
    }
  }

  if (confirming) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-xs text-red-300">确定删除「{gameTitle}」吗？此操作不可恢复。</p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={deleting}
            onClick={handleDelete}
            className="rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {deleting ? "删除中..." : "确认删除"}
          </button>
          <button
            type="button"
            disabled={deleting}
            onClick={() => { setConfirming(false); setErrorMessage(null); }}
            className="rounded-full border border-white/20 bg-white/[0.04] px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50"
          >
            取消
          </button>
        </div>
        {errorMessage ? <p className="text-xs text-red-300">{errorMessage}</p> : null}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="rounded-full border border-red-400/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-300 transition hover:bg-red-500/20"
    >
      删除
    </button>
  );
}
