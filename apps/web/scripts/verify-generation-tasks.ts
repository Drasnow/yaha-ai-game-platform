import assert from "node:assert/strict";

import {
  buildGenerationTaskResponse,
  generationTaskCreateSchema,
  normalizeAgentLogs,
} from "../lib/generation-tasks";

const parsed = generationTaskCreateSchema.parse({
  prompt: "  做一个点击星星得分小游戏  ",
  assetIds: ["asset_1", "asset_1", "asset_2"],
});

assert.equal(parsed.prompt, "做一个点击星星得分小游戏");
assert.deepEqual(parsed.assetIds, ["asset_1", "asset_2"]);
assert.equal(generationTaskCreateSchema.safeParse({ prompt: "hi" }).success, false);

const logs = normalizeAgentLogs([
  { agent_name: "RequirementAgent", step: "parse_prompt", message: "已解析创意" },
  { agentName: "GameDesignAgent", step: "design_rules", message: "已生成规则" },
]);

assert.deepEqual(logs, [
  { agentName: "RequirementAgent", step: "parse_prompt", message: "已解析创意" },
  { agentName: "GameDesignAgent", step: "design_rules", message: "已生成规则" },
]);

const response = buildGenerationTaskResponse({
  id: "task_1",
  prompt: parsed.prompt,
  status: "SUCCEEDED",
  currentStep: "complete",
  resultGameId: "game_1",
  resultVersionId: "version_1",
  errorMessage: null,
  createdAt: new Date("2026-01-01T00:00:00.000Z"),
  updatedAt: new Date("2026-01-01T00:00:01.000Z"),
});

assert.equal(response.task.status, "succeeded");
assert.equal(response.task.resultGameId, "game_1");
assert.equal(response.task.createdAt, "2026-01-01T00:00:00.000Z");

console.log("generation task rules ok");
