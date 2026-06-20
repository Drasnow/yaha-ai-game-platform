import { NextResponse } from "next/server";
import { z } from "zod";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type RouteContext = {
  params: Promise<{
    gameId: string;
  }>;
};

const updateGameSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "请输入游戏标题")
    .max(80, "标题不能超过 80 个字")
    .optional(),
  description: z
    .string()
    .trim()
    .min(1, "请输入游戏简介")
    .max(1000, "简介不能超过 1000 个字")
    .optional(),
  coverUrl: z.string().trim().url("封面地址格式不正确").optional().or(z.literal("")),
  tags: z.array(z.string().trim().min(1).max(40)).max(10, "标签最多 10 个").optional(),
});

const gameSelect = {
  id: true,
  title: true,
  description: true,
  coverUrl: true,
  tags: true,
  status: true,
  latestVersionId: true,
  playCount: true,
  publishedAt: true,
  createdAt: true,
  updatedAt: true,
  versions: {
    orderBy: { version: "desc" },
    select: {
      id: true,
      version: true,
      manifestUrl: true,
      entryUrl: true,
      artifactBaseUrl: true,
      entryFile: true,
      runtime: true,
      createdAt: true,
    },
  },
} as const;

export async function GET(_request: Request, context: RouteContext) {
  const user = await getCurrentUser();
  const { gameId } = await context.params;

  const game = await prisma.game.findFirst({
    where: {
      id: gameId,
      OR: [
        { status: "PUBLISHED" },
        ...(user ? [{ authorId: user.id }] : []),
      ],
    },
    select: gameSelect,
  });

  if (!game) {
    return NextResponse.json({ error: "游戏不存在" }, { status: 404 });
  }

  return NextResponse.json({ game });
}

export async function PATCH(request: Request, context: RouteContext) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const { gameId } = await context.params;
  const body = await request.json().catch(() => null);
  const parsed = updateGameSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "请求参数不正确" },
      { status: 400 },
    );
  }

  const existingGame = await prisma.game.findFirst({
    where: {
      id: gameId,
      authorId: user.id,
    },
    select: { id: true },
  });

  if (!existingGame) {
    return NextResponse.json({ error: "游戏不存在" }, { status: 404 });
  }

  const { title, description, coverUrl, tags } = parsed.data;

  if (
    title === undefined &&
    description === undefined &&
    coverUrl === undefined &&
    tags === undefined
  ) {
    return NextResponse.json({ error: "没有可更新的字段" }, { status: 400 });
  }

  const game = await prisma.game.update({
    where: { id: gameId },
    data: {
      ...(title !== undefined ? { title } : {}),
      ...(description !== undefined ? { description } : {}),
      ...(coverUrl !== undefined ? { coverUrl: coverUrl || null } : {}),
      ...(tags !== undefined ? { tags } : {}),
    },
    select: gameSelect,
  });

  return NextResponse.json({ game });
}