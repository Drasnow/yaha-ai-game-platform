import type { PrismaClient } from "@prisma/client";

import { generateGameWithAgent, generateGameWithAgentStream } from "@/lib/agent-client";
import { normalizeAgentLogs } from "@/lib/generation-tasks";

type CurrentUser = {
  id: string;
};

type AssetForAgent = {
  id: string;
  publicUrl: string;
  mimeType: string;
};

type TaskSelect = {
  readonly id: true;
  readonly title: true;
  readonly prompt: true;
  readonly status: true;
  readonly currentStep: true;
  readonly resultGameId: true;
  readonly resultVersionId: true;
  readonly errorMessage: true;
  readonly createdAt: true;
  readonly updatedAt: true;
};

type GenerateGameWithAgent = typeof generateGameWithAgent;

type TaskResult = {
  id: string;
  title: string;
  prompt: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "DEGRADED";
  currentStep: string | null;
  resultGameId: string | null;
  resultVersionId: string | null;
  errorMessage: string | null;
  createdAt: Date;
  updatedAt: Date;
};

export async function createGenerationTask({
  prisma,
  taskSelect,
  user,
  title,
  prompt,
  assetIds,
  sourceGameId,
}: {
  prisma: PrismaClient;
  taskSelect: TaskSelect;
  user: CurrentUser;
  title: string;
  prompt: string;
  assetIds: string[];
  sourceGameId?: string;
}): Promise<TaskResult> {
  return prisma.generationTask.create({
    data: {
      userId: user.id,
      title,
      prompt,
      status: "PENDING",
      currentStep: "queued",
      ...(sourceGameId ? { sourceGameId } : {}),
      assets: assetIds.length
        ? {
            connect: assetIds.map((id) => ({ id })),
          }
        : undefined,
      agentLogs: {
        create: {
          agentName: "TaskCoordinator",
          step: "queued",
          message: sourceGameId
            ? "对已有游戏发起重新生成任务，等待 Agent 执行。"
            : "生成任务已创建，等待 Agent 执行。",
        },
      },
    },
    select: taskSelect,
  });
}

export async function runGenerationTask({
  prisma,
  taskSelect,
  taskId,
  user,
  prompt,
  assets,
  sourceGameId,
}: {
  prisma: PrismaClient;
  taskSelect: TaskSelect;
  taskId: string;
  user: CurrentUser;
  prompt: string;
  assets: AssetForAgent[];
  sourceGameId?: string;
}): Promise<void> {
  const taskSelectForUpdate = {
    id: true,
    title: true,
    status: true,
    currentStep: true,
    resultGameId: true,
    resultVersionId: true,
    errorMessage: true,
    createdAt: true,
    updatedAt: true,
  } as const;

  // 标记为 RUNNING
  await prisma.generationTask.update({
    where: { id: taskId },
    data: { status: "RUNNING", currentStep: "agent_generate", errorMessage: null },
    select: taskSelectForUpdate,
  });

  // 收集最终结果（流结束后写入 DB）
  let artifactData: {
    manifest_url: string;
    entry_url: string;
    artifact_base_url: string;
  } | null = null;
  let finalLogs: Array<{ agentName: string; step: string; message: string }> = [];

  try {
    const streamGenerator = generateGameWithAgentStream(
      {
        task_id: taskId,
        user_id: user.id,
        prompt,
        assets: assets.map((asset) => ({
          asset_id: asset.id,
          url: asset.publicUrl,
          mime_type: asset.mimeType,
        })),
      },
      {
        onLog: async (log) => {
          // 每收到一条日志，立即写入数据库
          await prisma.agentLog.create({
            data: {
              taskId,
              agentName: log.agent,
              step: log.step,
              message: log.message,
            },
          });
          finalLogs.push({ agentName: log.agent, step: log.step, message: log.message });
        },
        onStep: async (step) => {
          // 每步更新 currentStep，前端 SSE 可轮询感知最新步骤
          await prisma.generationTask.update({
            where: { id: taskId },
            data: { currentStep: step },
          }).catch(() => {});
        },
        onRejected: async (feedback) => {
          throw Object.assign(new Error(`[USER_REJECTED] ${feedback}`), { _isRejected: true });
        },
        onError: async (message) => {
          // 非致命错误记录到日志，不中断流程
          console.warn(`[generation-task] agent stream error: ${message}`);
        },
      },
    );

    for await (const event of streamGenerator) {
      if (event.type === "artifact") {
        artifactData = {
          manifest_url: event.manifest_url,
          entry_url: event.entry_url,
          artifact_base_url: event.artifact_base_url,
        };
      }
      if (event.type === "end") {
        break;
      }
    }

    // 流结束，检查是否成功
    if (!artifactData) {
      throw new Error("AI出现网络故障，未返回生成游戏，请稍后重试");
    }

    // 获取 title/description/tags（需要从最后一个 unified_design log 或 agent 端返回）
    // 目前 fallback 模式下用 prompt 提取，后续可扩展
    const description = `根据创意生成的游戏：${prompt.slice(0, 50)}`;
    const tags: string[] = ["generated", "ai"];

    await prisma.$transaction(async (tx) => {
      let gameId: string;

      if (sourceGameId) {
        await tx.game.update({
          where: { id: sourceGameId },
          data: { description, tags },
        });
        gameId = sourceGameId;
      } else {
        const newGame = await tx.game.create({
          data: {
            authorId: user.id,
            title: (
              await tx.generationTask.findUnique({ where: { id: taskId }, select: { title: true } })
            )?.title ?? "AI 生成游戏",
            description,
            tags,
            status: "DRAFT",
          },
          select: { id: true },
        });
        gameId = newGame.id;
      }

      const latestVersion = await tx.gameVersion.findFirst({
        where: { gameId },
        orderBy: { version: "desc" },
        select: { version: true },
      });
      const nextVersion = (latestVersion?.version ?? 0) + 1;

      const version = await tx.gameVersion.create({
        data: {
          gameId,
          version: nextVersion,
          manifestUrl: artifactData!.manifest_url,
          entryUrl: artifactData!.entry_url,
          artifactBaseUrl: artifactData!.artifact_base_url,
          entryFile: "index.html",
          runtime: "iframe-html-v1",
          sourceTaskId: taskId,
          resultTaskId: taskId,
        },
        select: { id: true },
      });

      await tx.game.update({
        where: { id: gameId },
        data: { latestVersionId: version.id },
      });

      await tx.generationTask.update({
        where: { id: taskId },
        data: {
          status: "SUCCEEDED",
          currentStep: "complete",
          resultGameId: gameId,
          resultVersionId: version.id,
          errorMessage: null,
        },
      });
    });
  } catch (error) {
    const err = error as Error & { _isRejected?: boolean };
    if (err._isRejected) {
      // 用户输入无效，属于业务错误，不走 FAILED 状态但记录 feedback
      await prisma.generationTask.update({
        where: { id: taskId },
        data: {
          status: "FAILED",
          currentStep: "rejected",
          errorMessage: err.message,
        },
        select: taskSelectForUpdate,
      }).catch(() => {});
      return;
    }
    const message = err.message || "生成任务执行失败";
    await prisma.generationTask.update({
      where: { id: taskId },
      data: {
        status: "FAILED",
        currentStep: "failed",
        errorMessage: message,
        agentLogs: {
          create: {
            agentName: "TaskCoordinator",
            step: "failed",
            message,
          },
        },
      },
      select: taskSelectForUpdate,
    }).catch(() => {});
  }
}

export async function createAndRunGenerationTask({
  prisma,
  taskSelect,
  user,
  title,
  prompt,
  assetIds,
  assets,
  sourceGameId,
  generate = generateGameWithAgent,
}: {
  prisma: PrismaClient;
  taskSelect: TaskSelect;
  user: CurrentUser;
  title: string;
  prompt: string;
  assetIds: string[];
  assets: AssetForAgent[];
  sourceGameId?: string;
  generate?: GenerateGameWithAgent;
}): Promise<TaskResult> {
  const task = await createGenerationTask({ prisma, taskSelect, user, title, prompt, assetIds, sourceGameId });

  await runGenerationTask({
    prisma,
    taskSelect,
    taskId: task.id,
    user,
    prompt,
    assets,
    sourceGameId,
  });

  return prisma.generationTask.findUniqueOrThrow({
    where: { id: task.id },
    select: taskSelect,
  });
}
