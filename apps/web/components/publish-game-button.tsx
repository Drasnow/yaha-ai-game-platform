"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type PublishGameButtonProps = {
  gameId: string;
  disabled?: boolean;
};

export function PublishGameButton({ gameId, disabled = false }: PublishGameButtonProps) {
  const router = useRouter();
  const [isPublishing, setIsPublishing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handlePublish() {
    setIsPublishing(true);
    setErrorMessage(null);

    try {
      const response = await fetch(`/api/v1/games/${gameId}/publish`, { method: "POST" });
      const payload = (await response.json().catch(() => null)) as { error?: string } | null;

      if (!response.ok) {
        throw new Error(payload?.error ?? "发布失败");
      }

      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "发布失败");
    } finally {
      setIsPublishing(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={disabled || isPublishing}
        onClick={handlePublish}
        className="rounded-full bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPublishing ? "发布中..." : "发布"}
      </button>
      {disabled ? <p className="text-xs text-zinc-500">缺少可发布版本产物</p> : null}
      {errorMessage ? <p className="text-xs text-red-300">{errorMessage}</p> : null}
    </div>
  );
}
