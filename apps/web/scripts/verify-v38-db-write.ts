import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

function loadDotEnv() {
  if (!existsSync(".env")) {
    return;
  }

  for (const line of readFileSync(".env", "utf-8").replace(/\r/g, "").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    let value = trimmed.slice(separatorIndex + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    process.env[key] ??= value;
  }
}

async function main() {
  loadDotEnv();

  const [{ createAndRunGenerationTask }, { prisma }] = await Promise.all([
    import("../lib/generation-task-runner"),
    import("../lib/prisma"),
  ]);

  const taskSelect = {
    id: true,
    prompt: true,
    status: true,
    currentStep: true,
    resultGameId: true,
    resultVersionId: true,
    errorMessage: true,
    createdAt: true,
    updatedAt: true,
  } as const;

  const runId = Date.now();
  const user = await prisma.user.create({
    data: {
      email: `v38-${runId}@yaha.local`,
      passwordHash: "verify-only",
      displayName: "V3.8 Verify User",
    },
    select: { id: true },
  });

  try {
    const succeededTask = await createAndRunGenerationTask({
      prisma,
      taskSelect,
      user,
      prompt: "做一个点击星星得分的小游戏，30 秒内尽量多得分",
      assetIds: [],
      assets: [],
      generate: async (request) => ({
        status: "succeeded",
        title: "V3.8 数据库写入验证游戏",
        description: `由任务 ${request.task_id} 生成的验证产物`,
        tags: ["click", "verify", "v38"],
        artifact: {
          manifest_url: `http://localhost:9000/yaha-games/games/generated/${request.task_id}/v1/manifest.json`,
          entry_url: `http://localhost:9000/yaha-games/games/generated/${request.task_id}/v1/index.html`,
          artifact_base_url: `http://localhost:9000/yaha-games/games/generated/${request.task_id}/v1/`,
        },
        logs: [
          { agent_name: "RequirementAgent", step: "parse_prompt", message: "已解析玩法类型：点击得分" },
          { agent_name: "GameDesignAgent", step: "design_rules", message: "生成 30 秒计时和得分规则" },
          { agent_name: "CodeGenerationAgent", step: "render_files", message: "生成 index.html/style.css/game.js/manifest.json" },
          { agent_name: "BuildValidateAgent", step: "validate", message: "产物结构校验通过" },
          { agent_name: "ArtifactAgent", step: "upload", message: "产物已上传对象存储" },
        ],
      }),
    });

    assert.equal(succeededTask.status, "SUCCEEDED");
    assert.equal(succeededTask.currentStep, "complete");
    assert.ok(succeededTask.resultGameId);
    assert.ok(succeededTask.resultVersionId);
    assert.equal(succeededTask.errorMessage, null);

    const persistedSuccess = await prisma.generationTask.findUniqueOrThrow({
      where: { id: succeededTask.id },
      include: {
        resultGame: true,
        resultVersion: true,
        agentLogs: { orderBy: { createdAt: "asc" } },
      },
    });

    assert.equal(persistedSuccess.resultGame?.status, "DRAFT");
    assert.equal(persistedSuccess.resultGame?.latestVersionId, succeededTask.resultVersionId);
    assert.equal(persistedSuccess.resultVersion?.sourceTaskId, succeededTask.id);
    assert.equal(persistedSuccess.resultVersion?.resultTaskId, succeededTask.id);
    assert.equal(persistedSuccess.agentLogs.some((log) => log.agentName === "RequirementAgent"), true);
    assert.equal(persistedSuccess.agentLogs.length, 6);

    const failedTask = await createAndRunGenerationTask({
      prisma,
      taskSelect,
      user,
      prompt: "做一个会失败的生成任务",
      assetIds: [],
      assets: [],
      generate: async () => {
        throw new Error("模拟 Agent 失败");
      },
    });

    assert.equal(failedTask.status, "FAILED");
    assert.equal(failedTask.currentStep, "failed");
    assert.equal(failedTask.errorMessage, "模拟 Agent 失败");
    assert.equal(failedTask.resultGameId, null);
    assert.equal(failedTask.resultVersionId, null);

    const persistedFailure = await prisma.generationTask.findUniqueOrThrow({
      where: { id: failedTask.id },
      include: { agentLogs: true },
    });

    assert.equal(persistedFailure.agentLogs.some((log) => log.step === "failed"), true);

    console.log("v3.8 database write ok", {
      succeededTaskId: succeededTask.id,
      gameId: succeededTask.resultGameId,
      versionId: succeededTask.resultVersionId,
      failedTaskId: failedTask.id,
    });
  } finally {
    await prisma.user.delete({ where: { id: user.id } }).catch(() => undefined);
    await prisma.$disconnect();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
