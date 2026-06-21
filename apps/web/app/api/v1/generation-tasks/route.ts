import { NextResponse } from "next/server";

import {
  buildGenerationTaskResponse,
  generationTaskCreateSchema,
  serializeGenerationTask,
} from "@/lib/generation-tasks";
import { createAndRunGenerationTask } from "@/lib/generation-task-runner";
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

  const task = await createAndRunGenerationTask({
    prisma,
    taskSelect,
    user,
    title: parsed.data.title,
    prompt: parsed.data.prompt,
    assetIds: parsed.data.assetIds,
    assets,
  });

  const status = task.status === "FAILED" ? 500 : 201;
  return NextResponse.json(buildGenerationTaskResponse(task), { status });
}
