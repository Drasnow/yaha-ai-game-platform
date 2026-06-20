import "dotenv/config";

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";
import { readFile } from "node:fs/promises";
import path from "node:path";

import { putObject, setBucketPublicReadPolicy } from "@/lib/storage";

const SAMPLE_GAME_DIR = path.resolve(process.cwd(), "..", "..", "tmp", "sample-game");
const OBJECT_PREFIX = "games/seed/sample-click-game/v1";
const DEMO_USER_EMAIL = "demo@yaha.local";

const contentTypes: Record<string, string> = {
  "index.html": "text/html; charset=utf-8",
  "style.css": "text/css; charset=utf-8",
  "game.js": "text/javascript; charset=utf-8",
  "manifest.json": "application/json; charset=utf-8",
};

const artifactFiles = ["index.html", "style.css", "game.js", "manifest.json"] as const;

const adapter = new PrismaPg({
  connectionString: process.env.DATABASE_URL,
});

const prisma = new PrismaClient({ adapter });

async function uploadArtifactFile(fileName: (typeof artifactFiles)[number]) {
  const filePath = path.join(SAMPLE_GAME_DIR, fileName);
  const body = await readFile(filePath);
  const objectKey = `${OBJECT_PREFIX}/${fileName}`;

  return putObject({
    key: objectKey,
    body,
    contentType: contentTypes[fileName],
  });
}

async function upsertSampleGame(artifactBaseUrl: string) {
  const user = await prisma.user.findUnique({
    where: { email: DEMO_USER_EMAIL },
    select: { id: true },
  });

  if (!user) {
    throw new Error(`Demo user not found: ${DEMO_USER_EMAIL}. Run pnpm prisma db seed first.`);
  }

  const manifestUrl = `${artifactBaseUrl}/manifest.json`;
  const entryUrl = `${artifactBaseUrl}/index.html`;

  const existingGame = await prisma.game.findFirst({
    where: {
      authorId: user.id,
      title: "星星收集挑战",
    },
    select: {
      id: true,
      latestVersionId: true,
      versions: {
        where: { version: 1 },
        select: { id: true },
        take: 1,
      },
    },
  });

  if (!existingGame) {
    const createdGame = await prisma.game.create({
      data: {
        authorId: user.id,
        title: "星星收集挑战",
        description: "30 秒内点击跳动的星星得分，用于验证 MinIO 远端游戏产物和 Play 动态加载。",
        coverUrl: null,
        tags: ["click", "minio", "remote-artifact"],
        status: "PUBLISHED",
        publishedAt: new Date(),
        versions: {
          create: {
            version: 1,
            manifestUrl,
            entryUrl,
            artifactBaseUrl,
            entryFile: "index.html",
            runtime: "iframe-static-html",
          },
        },
      },
      include: {
        versions: {
          where: { version: 1 },
          select: { id: true },
          take: 1,
        },
      },
    });

    const versionId = createdGame.versions[0]?.id;
    if (!versionId) {
      throw new Error("Created sample game without version");
    }

    await prisma.game.update({
      where: { id: createdGame.id },
      data: { latestVersionId: versionId },
    });

    return { gameId: createdGame.id, versionId, manifestUrl, entryUrl, artifactBaseUrl };
  }

  let versionId = existingGame.latestVersionId ?? existingGame.versions[0]?.id;

  if (versionId) {
    await prisma.gameVersion.update({
      where: { id: versionId },
      data: {
        manifestUrl,
        entryUrl,
        artifactBaseUrl,
        entryFile: "index.html",
        runtime: "iframe-static-html",
      },
    });
  } else {
    const createdVersion = await prisma.gameVersion.create({
      data: {
        gameId: existingGame.id,
        version: 1,
        manifestUrl,
        entryUrl,
        artifactBaseUrl,
        entryFile: "index.html",
        runtime: "iframe-static-html",
      },
      select: { id: true },
    });
    versionId = createdVersion.id;
  }

  await prisma.game.update({
    where: { id: existingGame.id },
    data: {
      description: "30 秒内点击跳动的星星得分，用于验证 MinIO 远端游戏产物和 Play 动态加载。",
      coverUrl: null,
      tags: ["click", "minio", "remote-artifact"],
      status: "PUBLISHED",
      latestVersionId: versionId,
      publishedAt: new Date(),
    },
  });

  return { gameId: existingGame.id, versionId, manifestUrl, entryUrl, artifactBaseUrl };
}

async function main() {
  await setBucketPublicReadPolicy();

  const uploads = [];

  for (const fileName of artifactFiles) {
    uploads.push(await uploadArtifactFile(fileName));
  }

  const artifactBaseUrl = uploads
    .find((upload) => upload.key.endsWith("/index.html"))
    ?.publicUrl.replace(/\/index\.html$/, "");

  if (!artifactBaseUrl) {
    throw new Error("Failed to derive artifact base URL");
  }

  const game = await upsertSampleGame(artifactBaseUrl);

  console.log(
    JSON.stringify(
      {
        uploadedFiles: uploads.map((upload) => ({ key: upload.key, publicUrl: upload.publicUrl })),
        game,
      },
      null,
      2,
    ),
  );
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });