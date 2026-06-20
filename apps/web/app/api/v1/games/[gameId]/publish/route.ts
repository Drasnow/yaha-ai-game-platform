import { NextResponse } from "next/server";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type RouteContext = {
  params: Promise<{
    gameId: string;
  }>;
};

function buildPlaceholderArtifact(gameId: string) {
  const baseUrl =
    process.env.MINIO_PUBLIC_URL ??
    `${process.env.MINIO_ENDPOINT ?? "http://localhost:9000"}/${process.env.MINIO_BUCKET ?? "yaha-games"}`;
  const artifactBaseUrl = `${baseUrl.replace(/\/$/, "")}/games/dev/${gameId}/v1`;

  return {
    manifestUrl: `${artifactBaseUrl}/manifest.json`,
    entryUrl: `${artifactBaseUrl}/index.html`,
    artifactBaseUrl,
  };
}

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

export async function POST(_request: Request, context: RouteContext) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const { gameId } = await context.params;
  const existingGame = await prisma.game.findFirst({
    where: { id: gameId, authorId: user.id },
    select: {
      id: true,
      latestVersionId: true,
      versions: {
        orderBy: { version: "desc" },
        take: 1,
        select: { id: true },
      },
    },
  });

  if (!existingGame) {
    return NextResponse.json({ error: "游戏不存在" }, { status: 404 });
  }

  const game = await prisma.$transaction(async (tx) => {
    let latestVersionId = existingGame.latestVersionId ?? existingGame.versions[0]?.id;

    if (!latestVersionId) {
      const artifact = buildPlaceholderArtifact(gameId);
      const version = await tx.gameVersion.create({
        data: {
          gameId,
          version: 1,
          manifestUrl: artifact.manifestUrl,
          entryUrl: artifact.entryUrl,
          artifactBaseUrl: artifact.artifactBaseUrl,
          entryFile: "index.html",
          runtime: "iframe-html-v1",
        },
        select: { id: true },
      });
      latestVersionId = version.id;
    }

    return tx.game.update({
      where: { id: gameId },
      data: {
        status: "PUBLISHED",
        latestVersionId,
        publishedAt: new Date(),
      },
      select: gameSelect,
    });
  });

  return NextResponse.json({ game });
}
