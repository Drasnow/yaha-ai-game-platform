import { Prisma } from "@prisma/client";
import { NextResponse } from "next/server";
import { z } from "zod";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const playEventSchema = z.object({
  gameId: z.string().trim().min(1, "缺少游戏 ID"),
  versionId: z.string().trim().min(1).optional().nullable(),
  eventType: z.enum(["load_start", "load_success", "load_failed", "play_start", "play_end"]),
  message: z.string().trim().max(1000).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

const eventTypeMap = {
  load_start: "LOAD_START",
  load_success: "LOAD_SUCCESS",
  load_failed: "LOAD_FAILED",
  play_start: "PLAY_START",
  play_end: "PLAY_END",
} as const;

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const parsed = playEventSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "请求参数不正确" },
      { status: 400 },
    );
  }

  const user = await getCurrentUser();
  const { gameId, versionId, eventType, message, metadata } = parsed.data;

  const game = await prisma.game.findFirst({
    where: {
      id: gameId,
      OR: [{ status: "PUBLISHED" }, ...(user ? [{ authorId: user.id }] : [])],
    },
    select: { id: true },
  });

  if (!game) {
    return NextResponse.json({ error: "游戏不存在" }, { status: 404 });
  }

  if (versionId) {
    const version = await prisma.gameVersion.findFirst({
      where: { id: versionId, gameId },
      select: { id: true },
    });

    if (!version) {
      return NextResponse.json({ error: "游戏版本不存在" }, { status: 404 });
    }
  }

  const playEvent = await prisma.playEvent.create({
    data: {
      gameId,
      versionId: versionId ?? null,
      userId: user?.id ?? null,
      eventType: eventTypeMap[eventType],
      message,
      metadata: metadata ? (metadata as Prisma.InputJsonObject) : undefined,
    },
    select: {
      id: true,
      gameId: true,
      versionId: true,
      eventType: true,
      createdAt: true,
    },
  });

  if (eventType === "load_success" || eventType === "play_start") {
    await prisma.game.update({
      where: { id: gameId },
      data: { playCount: { increment: 1 } },
      select: { id: true },
    });
  }

  return NextResponse.json({ playEvent }, { status: 201 });
}