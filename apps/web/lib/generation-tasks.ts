import { z } from "zod";

const taskStatusMap = {
  PENDING: "pending",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
} as const;

export type AgentLogInput = {
  agentName?: string;
  agent_name?: string;
  step: string;
  message: string;
};

export const generationTaskCreateSchema = z.object({
  prompt: z.string().trim().min(10, "创意描述至少需要 10 个字").max(2000, "创意描述不能超过 2000 个字"),
  assetIds: z
    .array(z.string().trim().min(1))
    .optional()
    .default([])
    .transform((assetIds) => Array.from(new Set(assetIds))),
});

export function normalizeAgentLogs(logs: AgentLogInput[]) {
  return logs.map((log) => ({
    agentName: log.agentName ?? log.agent_name ?? "Agent",
    step: log.step,
    message: log.message,
  }));
}

type GenerationTaskForResponse = {
  id: string;
  prompt: string;
  status: keyof typeof taskStatusMap;
  currentStep: string | null;
  resultGameId: string | null;
  resultVersionId: string | null;
  errorMessage: string | null;
  createdAt: Date;
  updatedAt: Date;
};

export function serializeGenerationTask(task: GenerationTaskForResponse) {
  return {
    id: task.id,
    prompt: task.prompt,
    status: taskStatusMap[task.status],
    currentStep: task.currentStep,
    resultGameId: task.resultGameId,
    resultVersionId: task.resultVersionId,
    errorMessage: task.errorMessage,
    createdAt: task.createdAt.toISOString(),
    updatedAt: task.updatedAt.toISOString(),
  };
}

export function buildGenerationTaskResponse(task: GenerationTaskForResponse) {
  return { task: serializeGenerationTask(task) };
}
