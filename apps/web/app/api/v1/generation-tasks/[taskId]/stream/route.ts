import { NextResponse } from "next/server";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type RouteContext = {
  params: Promise<{ taskId: string }>;
};

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: RouteContext) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const { taskId } = await context.params;

  const task = await prisma.generationTask.findFirst({
    where: { id: taskId, userId: user.id },
    select: { id: true, status: true, currentStep: true },
  });

  if (!task) {
    return NextResponse.json({ error: "任务不存在" }, { status: 404 });
  }

  // 已知 Agent 总步骤数（固定值，不随任务变化）
  const TOTAL_STEPS = 25;

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      const send = (data: object) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      try {
        send({
          type: "task",
          status: task.status,
          currentStep: task.currentStep,
          totalSteps: TOTAL_STEPS,
          currentStepIndex: 0,
        });

        let lastLogCount = 0;

        while (true) {
          await new Promise((r) => setTimeout(r, 600));

          const currentTask = await prisma.generationTask.findFirst({
            where: { id: taskId },
            select: {
              status: true,
              currentStep: true,
              resultGameId: true,
              resultVersionId: true,
              errorMessage: true,
            },
          });

          if (!currentTask) {
            send({ type: "done", status: "failed", errorMessage: "任务已删除" });
            break;
          }

          const logs = await prisma.agentLog.findMany({
            where: { taskId },
            orderBy: { createdAt: "asc" },
            select: { agentName: true, step: true, message: true, createdAt: true },
          });

          const isFinished = currentTask.status === "SUCCEEDED" || currentTask.status === "FAILED";

          if (isFinished) {
            // 任务完成时：发送最新一条日志（只显示最后一条）
            const latest = logs.length > 0 ? logs[logs.length - 1] : null;
            const progress = Math.min(Math.round((logs.length / TOTAL_STEPS) * 100), 100);
            send({
              type: "done",
              status: currentTask.status,
              currentStep: currentTask.currentStep,
              currentStepIndex: logs.length,
              totalSteps: TOTAL_STEPS,
              progress,
              errorMessage: currentTask.errorMessage,
              resultGameId: currentTask.resultGameId,
              resultVersionId: currentTask.resultVersionId,
              latestLog: latest
                ? { agentName: latest.agentName, step: latest.step, message: latest.message }
                : null,
              logs: logs.map((l) => ({ agentName: l.agentName, step: l.step, message: l.message })),
            });
            break;
          }

          // 任务进行中：仅当有新增日志时才推送最新一条
          if (logs.length !== lastLogCount) {
            lastLogCount = logs.length;
            const latest = logs[logs.length - 1];
            const progress = Math.min(Math.round((logs.length / TOTAL_STEPS) * 100), 100);
            send({
              type: "update",
              currentStep: currentTask.currentStep,
              currentStepIndex: logs.length,
              totalSteps: TOTAL_STEPS,
              progress,
              latestLog: { agentName: latest.agentName, step: latest.step, message: latest.message },
            });
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "流式传输异常";
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "error", message: msg })}\n\n`));
      } finally {
        controller.close();
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
