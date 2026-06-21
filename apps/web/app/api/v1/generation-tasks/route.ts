import { NextResponse } from "next/server";
import { after } from "next/server";

import {
  buildGenerationTaskResponse,
  generationTaskCreateSchema,
  serializeGenerationTask,
} from "@/lib/generation-tasks";
import { createGenerationTask, runGenerationTask } from "@/lib/generation-task-runner";
import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const taskSelect = {
  id: true,
  title: true,
  prompt: true,
  status: true,
  currentStep: true,
  resultGameId: true,
  resultVersionId: true,
  errorMessage: true,
  createdAt: true,
  updatedAt: true,
} as const;

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const tasks = await prisma.generationTask.findMany({
    where: { userId: user.id },
    orderBy: { createdAt: "desc" },
    take: 20,
    select: taskSelect,
  });

  return NextResponse.json({ tasks: tasks.map(serializeGenerationTask) });
}

export async function POST(request: Request) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  const parsed = generationTaskCreateSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "请求参数不正确" },
      { status: 400 },
    );
  }

  const assets = parsed.data.assetIds.length
    ? await prisma.asset.findMany({
        where: {
          id: { in: parsed.data.assetIds },
          ownerId: user.id,
        },
        select: {
          id: true,
          publicUrl: true,
          mimeType: true,
        },
      })
    : [];

  if (assets.length !== parsed.data.assetIds.length) {
    return NextResponse.json({ error: "素材不存在或无权使用" }, { status: 400 });
  }

  if (parsed.data.gameId) {
    const game = await prisma.game.findFirst({
      where: { id: parsed.data.gameId, authorId: user.id },
      select: { id: true },
    });
    if (!game) {
      return NextResponse.json({ error: "游戏不存在或无权操作" }, { status: 404 });
    }
  }

  // 1. 创建任务记录，立即返回
  const task = await createGenerationTask({
    prisma,
    taskSelect,
    user,
    title: parsed.data.title,
    prompt: parsed.data.prompt,
    assetIds: parsed.data.assetIds,
    ...(parsed.data.gameId ? { sourceGameId: parsed.data.gameId } : {}),
  });

  const responseTask = {
    ...task,
    status: task.status === "PENDING" ? "pending" : task.status === "RUNNING" ? "running" : task.status,
  };

  // 2. 立即返回 taskId，前端可以用这个 ID 建立 SSE 连接
  const response = NextResponse.json(
    {
      task: {
        id: task.id,
        title: task.title,
        prompt: task.prompt,
        status: "pending",
        currentStep: task.currentStep,
        resultGameId: task.resultGameId,
        resultVersionId: task.resultVersionId,
        errorMessage: task.errorMessage,
        createdAt: task.createdAt.toISOString(),
        updatedAt: task.updatedAt.toISOString(),
      },
    },
    { status: 201 },
  );

  // 3. 在响应发送后异步执行生成任务
  after(async () => {
    try {
      await runGenerationTask({
        prisma,
        taskSelect,
        taskId: task.id,
        user,
        prompt: parsed.data.prompt,
        assets,
        sourceGameId: parsed.data.gameId,
      });
    } catch (err) {
      // 错误已在 runGenerationTask 内部写入数据库
      console.error(`[generation-task] background run failed for task ${task.id}:`, err);
    }
  });

  return response;
}
