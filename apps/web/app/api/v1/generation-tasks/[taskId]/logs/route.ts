import { NextResponse } from "next/server";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { normalizeAgentLogs, type AgentLogInput } from "@/lib/generation-tasks";

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
    select: { id: true },
  });

  if (!task) {
    return NextResponse.json({ error: "任务不存在" }, { status: 404 });
  }

  const logs = await prisma.agentLog.findMany({
    where: { taskId },
    orderBy: { createdAt: "asc" },
    select: {
      id: true,
      agentName: true,
      step: true,
      message: true,
      rawPayload: true,
      createdAt: true,
    },
  });

  return NextResponse.json({
    logs: logs.map((log) => ({
      ...log,
      createdAt: log.createdAt.toISOString(),
    })),
  });
}

export async function POST(request: Request, context: RouteContext) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const { taskId } = await context.params;

  const task = await prisma.generationTask.findFirst({
    where: { id: taskId, userId: user.id },
    select: { id: true },
  });

  if (!task) {
    return NextResponse.json({ error: "任务不存在" }, { status: 404 });
  }

  const body = await request.json().catch(() => null);
  if (!body || !Array.isArray(body.logs)) {
    return NextResponse.json({ error: "请求体需要包含 logs 数组" }, { status: 400 });
  }

  const logs: AgentLogInput[] = body.logs;

  if (!logs.length) {
    return NextResponse.json({ error: "logs 数组不能为空" }, { status: 400 });
  }

  const normalized = normalizeAgentLogs(logs);

  await prisma.agentLog.createMany({
    data: normalized.map((log) => ({
      taskId,
      agentName: log.agentName,
      step: log.step,
      message: log.message,
    })),
  });

  if (body.currentStep) {
    await prisma.generationTask.update({
      where: { id: taskId },
      data: { currentStep: body.currentStep },
    }).catch(() => {});
  }

  return NextResponse.json({ ok: true, count: normalized.length });
}
