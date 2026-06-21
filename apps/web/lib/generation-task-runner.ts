import type { PrismaClient } from "@prisma/client";

import { generateGameWithAgent } from "@/lib/agent-client";
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

export async function createAndRunGenerationTask({
  prisma,
  taskSelect,
  user,
  prompt,
  assetIds,
  assets,
  generate = generateGameWithAgent,
}: {
  prisma: PrismaClient;
  taskSelect: TaskSelect;
  user: CurrentUser;
  prompt: string;
  assetIds: string[];
  assets: AssetForAgent[];
  generate?: GenerateGameWithAgent;
}) {
  let task = await prisma.generationTask.create({
    data: {
      userId: user.id,
      prompt,
      status: "PENDING",
      currentStep: "queued",
      assets: assetIds.length
        ? {
            connect: assetIds.map((id) => ({ id })),
          }
        : undefined,
      agentLogs: {
        create: {
          agentName: "TaskCoordinator",
          step: "queued",
          message: "生成任务已创建，等待 Agent 执行。",
        },
      },
    },
    select: taskSelect,
  });

  task = await prisma.generationTask.update({
    where: { id: task.id },
    data: { status: "RUNNING", currentStep: "agent_generate", errorMessage: null },
    select: taskSelect,
  });

  try {
    const agentResult = await generate({
      task_id: task.id,
      user_id: user.id,
      prompt,
      assets: assets.map((asset) => ({
        asset_id: asset.id,
        url: asset.publicUrl,
        mime_type: asset.mimeType,
      })),
    });

    if (agentResult.status !== "succeeded") {
      throw new Error("Agent 生成失败");
    }

    const logs = normalizeAgentLogs(agentResult.logs);
    return prisma.$transaction(async (tx) => {
      const game = await tx.game.create({
        data: {
          authorId: user.id,
          title: agentResult.title,
          description: agentResult.description,
          tags: agentResult.tags,
          status: "DRAFT",
        },
        select: { id: true },
      });

      const version = await tx.gameVersion.create({
        data: {
          gameId: game.id,
          version: 1,
          manifestUrl: agentResult.artifact.manifest_url,
          entryUrl: agentResult.artifact.entry_url,
          artifactBaseUrl: agentResult.artifact.artifact_base_url,
          entryFile: "index.html",
          runtime: "iframe-html-v1",
          sourceTaskId: task.id,
          resultTaskId: task.id,
        },
        select: { id: true },
      });

      await tx.game.update({
        where: { id: game.id },
        data: { latestVersionId: version.id },
      });

      if (logs.length) {
        await tx.agentLog.createMany({
          data: logs.map((log) => ({
            taskId: task.id,
            agentName: log.agentName,
            step: log.step,
            message: log.message,
          })),
        });
      }

      return tx.generationTask.update({
        where: { id: task.id },
        data: {
          status: "SUCCEEDED",
          currentStep: "complete",
          resultGameId: game.id,
          resultVersionId: version.id,
          errorMessage: null,
        },
        select: taskSelect,
      });
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "生成任务执行失败";
    return prisma.generationTask.update({
      where: { id: task.id },
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
      select: taskSelect,
    });
  }
}
