import { NextResponse } from "next/server";
import { z } from "zod";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const gameplayTypes = ["quiz", "story", "puzzle", "simulation"] as const;

const createGameSchema = z.object({
  title: z.string().trim().min(1, "请输入游戏标题").max(80, "标题不能超过 80 个字"),
  description: z
    .string()
    .trim()
    .min(1, "请输入游戏简介")
    .max(1000, "简介不能超过 1000 个字"),
  gameplayType: z.enum(gameplayTypes, "请选择有效的玩法类型"),
});

const gameplayTypeLabels: Record<(typeof gameplayTypes)[number], string> = {
  quiz: "问答闯关",
  story: "剧情选择",
  puzzle: "解谜挑战",
  simulation: "经营模拟",
};

const gameSelect = {
  id: true,
  title: true,
  description: true,
  tags: true,
  status: true,
  playCount: true,
  createdAt: true,
  updatedAt: true,
} as const;

export async function GET() {
  const games = await prisma.game.findMany({
    where: { status: "PUBLISHED" },
    orderBy: { publishedAt: "desc" },
    select: gameSelect,
  });

  return NextResponse.json({ games });
}

export async function POST(request: Request) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  const parsed = createGameSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "请求参数不正确" },
      { status: 400 },
    );
  }

  const { title, description, gameplayType } = parsed.data;

  const game = await prisma.game.create({
    data: {
      authorId: user.id,
      title,
      description,
      tags: [gameplayType, gameplayTypeLabels[gameplayType]],
    },
    select: gameSelect,
  });

  return NextResponse.json({ game }, { status: 201 });
}
