import { NextResponse } from "next/server";

import { buildGenerationTaskResponse } from "@/lib/generation-tasks";
import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

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

type RouteContext = {
  params: Promise<{ taskId: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const { taskId } = await context.params;
  const task = await prisma.generationTask.findFirst({
    where: { id: taskId, userId: user.id },
    select: taskSelect,
  });

  if (!task) {
    return NextResponse.json({ error: "任务不存在" }, { status: 404 });
  }

  return NextResponse.json(buildGenerationTaskResponse(task));
}
