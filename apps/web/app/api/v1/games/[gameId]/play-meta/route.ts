import { NextResponse } from "next/server";

import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type RouteContext = {
  params: Promise<{
    gameId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const user = await getCurrentUser();
  const { gameId } = await context.params;

  const game = await prisma.game.findFirst({
    where: {
      id: gameId,
      OR: [{ status: "PUBLISHED" }, ...(user ? [{ authorId: user.id }] : [])],
    },
    select: {
      id: true,
      title: true,
      description: true,
      coverUrl: true,
      tags: true,
      status: true,
      author: {
        select: {
          id: true,
          displayName: true,
          email: true,
        },
      },
      latestVersion: {
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
      versions: {
        orderBy: { version: "desc" },
        take: 1,
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
    },
  });

  if (!game) {
    return NextResponse.json({ error: "游戏不存在" }, { status: 404 });
  }

  const version = game.latestVersion ?? game.versions[0];

  if (!version) {
    return NextResponse.json({ error: "游戏还没有可加载的版本产物" }, { status: 409 });
  }

  return NextResponse.json({
    game: {
      id: game.id,
      title: game.title,
      description: game.description,
      coverUrl: game.coverUrl,
      tags: game.tags,
      status: game.status,
      author: game.author,
    },
    playMeta: {
      versionId: version.id,
      version: version.version,
      manifestUrl: version.manifestUrl,
      entryUrl: version.entryUrl ?? `${version.artifactBaseUrl.replace(/\/$/, "")}/${version.entryFile}`,
      artifactBaseUrl: version.artifactBaseUrl,
      entryFile: version.entryFile,
      runtime: version.runtime,
      createdAt: version.createdAt,
    },
  });
}
