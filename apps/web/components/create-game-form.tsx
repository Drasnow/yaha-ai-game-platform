"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type TaskStatus = "idle" | "pending" | "running" | "succeeded" | "failed";

type AgentLog = {
  agentName: string;
  step: string;
  message: string;
};

type GenerationTask = {
  id: string;
  prompt: string;
  status: Exclude<TaskStatus, "idle">;
  currentStep: string | null;
  resultGameId: string | null;
  resultVersionId: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
};

type TaskHistoryItem = {
  id: string;
  title: string;
  status: Exclude<TaskStatus, "idle">;
  createdAt: string;
  resultGameId: string | null;
};

function statusLabel(status: TaskStatus) {
  const labels: Record<TaskStatus, string> = {
    idle: "未开始",
    pending: "等待创建任务",
    running: "Agent 生成中",
    succeeded: "生成成功",
    failed: "生成失败",
  };

  return labels[status];
}

function statusClassName(status: TaskStatus) {
  if (status === "succeeded") {
    return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
  }

  if (status === "failed") {
    return "border-red-400/30 bg-red-500/10 text-red-200";
  }

  if (status === "running" || status === "pending") {
    return "border-indigo-400/30 bg-indigo-500/10 text-indigo-200";
  }

  return "border-white/10 bg-white/[0.04] text-zinc-300";
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload && typeof payload === "object" && "error" in payload
      ? String(payload.error)
      : `请求失败：${response.status}`;
    throw new Error(message);
  }

  return payload as T;
}

export function CreateGameForm() {
  const [taskStatus, setTaskStatus] = useState<TaskStatus>("idle");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [promptPreview, setPromptPreview] = useState("");
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [currentTask, setCurrentTask] = useState<GenerationTask | null>(null);
  const [publishedGameIds, setPublishedGameIds] = useState<Set<string>>(new Set());

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const prompt = String(formData.get("prompt") ?? "").trim();
    const file = formData.get("asset");

    if (prompt.length < 10) {
      setTaskStatus("failed");
      setMessage("创意描述至少需要 10 个字。");
      return;
    }

    setPromptPreview(prompt);
    setTaskStatus("running");
    setMessage("正在上传素材并创建生成任务，请稍候...");
    setAgentLogs([
      { agentName: "TaskCoordinator", step: "submitting", message: "前端正在提交 Create 请求。" },
    ]);
    setCurrentTask(null);

    try {
      const assetIds: string[] = [];

      if (file instanceof File && file.size > 0) {
        const uploadData = new FormData();
        uploadData.append("file", file);
        const uploadResult = await readJson<{ assetId: string }>(
          await fetch("/api/v1/assets/upload", {
            method: "POST",
            body: uploadData,
          }),
        );
        assetIds.push(uploadResult.assetId);
      }

      setMessage("素材处理完成，正在调用 FastAPI Agent 生成游戏...");

      const taskResult = await readJson<{ task: GenerationTask }>(
        await fetch("/api/v1/generation-tasks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, assetIds }),
        }),
      );

      const task = taskResult.task;
      setCurrentTask(task);
      setTaskStatus(task.status);
      setMessage(task.status === "succeeded" ? "生成任务已完成，可以预览或发布游戏。" : task.errorMessage ?? "生成任务已提交。");
      setTaskHistory((items) =>
        ([
          {
            id: task.id,
            title: prompt.slice(0, 28),
            status: task.status,
            createdAt: new Date(task.createdAt).toLocaleString("zh-CN"),
            resultGameId: task.resultGameId,
          },
          ...items,
        ] satisfies TaskHistoryItem[]).slice(0, 5),
      );

      const logsResult = await readJson<{ logs: AgentLog[] }>(
        await fetch(`/api/v1/generation-tasks/${task.id}/logs`),
      );
      setAgentLogs(logsResult.logs);
      form.reset();
      setSelectedFileName(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "创建生成任务失败";
      setTaskStatus("failed");
      setMessage(errorMessage);
      setAgentLogs((logs) => [
        ...logs,
        { agentName: "TaskCoordinator", step: "failed", message: errorMessage },
      ]);
    }
  }

  async function handlePublish() {
    if (!currentTask?.resultGameId) {
      return;
    }

    setMessage("正在发布游戏...");
    try {
      await readJson<{ game: unknown }>(
        await fetch(`/api/v1/games/${currentTask.resultGameId}/publish`, { method: "POST" }),
      );
      setPublishedGameIds((ids) => new Set(ids).add(currentTask.resultGameId!));
      setMessage("发布成功，首页现在可以看到这个游戏。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "发布失败");
    }
  }

  return (
    <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
      <form
        onSubmit={handleSubmit}
        className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 text-left shadow-2xl shadow-black/20 sm:p-8"
      >
        <div className="space-y-2">
          <p className="text-sm font-medium text-indigo-300">V3.5 FastAPI Agent 生成入口</p>
          <h2 className="text-2xl font-semibold">描述你的互动游戏创意</h2>
          <p className="text-sm leading-6 text-zinc-400">
            提交后会调用 Next.js generation task API，再由服务端请求 FastAPI Agent 的 /generate 接口生成并上传游戏产物。
          </p>
        </div>

        <div className="mt-8 space-y-6">
          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">创意文本</span>
            <textarea
              name="prompt"
              required
              rows={7}
              minLength={10}
              maxLength={2000}
              className="w-full resize-none rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3 text-white outline-none transition placeholder:text-zinc-600 focus:border-indigo-400"
              placeholder="例如：生成一个 30 秒点击星星得分小游戏，玩家点击越多分数越高。"
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span className="text-zinc-300">上传素材（可选）</span>
            <div className="rounded-2xl border border-dashed border-white/15 bg-zinc-900 p-5 transition hover:border-indigo-300/50">
              <input
                name="asset"
                type="file"
                accept="image/png,image/jpeg,image/webp,text/plain"
                className="block w-full text-sm text-zinc-400 file:mr-4 file:rounded-full file:border-0 file:bg-indigo-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-indigo-400"
                onChange={(event) => setSelectedFileName(event.target.files?.[0]?.name ?? null)}
              />
              <p className="mt-3 text-xs leading-5 text-zinc-500">
                支持 PNG、JPEG、WEBP、TXT，单文件最大 10MB。上传后会随生成任务传给 Agent。
              </p>
              {selectedFileName ? (
                <p className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-zinc-300">
                  已选择：{selectedFileName}
                </p>
              ) : null}
            </div>
          </label>

          {message ? (
            <p className={`rounded-2xl border px-4 py-3 text-sm ${statusClassName(taskStatus)}`}>
              {message}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={taskStatus === "running"}
            className="w-full rounded-2xl bg-indigo-500 px-4 py-3 font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {taskStatus === "running" ? "生成中..." : "创建生成任务"}
          </button>
        </div>
      </form>

      <aside className="space-y-6">
        <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/20 sm:p-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-indigo-300">任务进度</p>
              <h2 className="mt-2 text-2xl font-semibold">{statusLabel(taskStatus)}</h2>
              {currentTask ? <p className="mt-2 text-xs text-zinc-500">任务 ID：{currentTask.id}</p> : null}
            </div>
            <span className={`rounded-full border px-3 py-1 text-xs ${statusClassName(taskStatus)}`}>
              {taskStatus.toUpperCase()}
            </span>
          </div>

          <div className="mt-6 space-y-3">
            {agentLogs.length ? agentLogs.map((log, index) => (
              <div key={`${log.agentName}-${log.step}-${index}`} className="rounded-2xl border border-white/10 bg-zinc-900 p-4">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-zinc-200">{index + 1}. {log.agentName}</span>
                  <span className="text-zinc-500">{log.step}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-400">{log.message}</p>
              </div>
            )) : (
              <p className="rounded-2xl border border-white/10 bg-zinc-900 p-4 text-sm text-zinc-400">
                提交任务后会显示真实 Agent 日志。
              </p>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 sm:p-8">
          <p className="text-sm text-indigo-300">生成结果</p>
          <h2 className="mt-2 text-2xl font-semibold">预览与发布</h2>
          {taskStatus === "succeeded" && currentTask?.resultGameId ? (
            <div className="mt-6 space-y-4 text-sm leading-6 text-zinc-300">
              <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-emerald-200">
                {publishedGameIds.has(currentTask.resultGameId)
                  ? "发布成功，游戏已进入首页。"
                  : "生成成功，游戏已保存为草稿。"}
              </p>
              <div>
                <p className="text-zinc-500">创意摘要</p>
                <p className="mt-1 text-zinc-200">{promptPreview}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href={`/play/${currentTask.resultGameId}?preview=1`}
                  className="rounded-full bg-emerald-500 px-5 py-2.5 font-medium text-white transition hover:bg-emerald-400"
                >
                  预览游戏
                </Link>
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={publishedGameIds.has(currentTask.resultGameId)}
                  className="rounded-full bg-indigo-500 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {publishedGameIds.has(currentTask.resultGameId) ? "已发布" : "发布游戏"}
                </button>
              </div>
            </div>
          ) : (
            <p className="mt-6 text-sm leading-6 text-zinc-400">
              生成成功后这里会展示预览链接和发布按钮。
            </p>
          )}
        </section>

        <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 sm:p-8">
          <p className="text-sm text-indigo-300">最近任务</p>
          <div className="mt-4 space-y-3">
            {taskHistory.length ? taskHistory.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/10 bg-zinc-900 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-zinc-200">{item.title}</p>
                  <span className={`rounded-full border px-2 py-1 text-[11px] ${statusClassName(item.status)}`}>
                    {item.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-zinc-500">{item.createdAt}</p>
                {item.resultGameId ? <p className="mt-1 text-xs text-zinc-500">Game ID：{item.resultGameId}</p> : null}
              </div>
            )) : (
              <p className="text-sm leading-6 text-zinc-400">暂无任务，提交创意后会显示最近记录。</p>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}