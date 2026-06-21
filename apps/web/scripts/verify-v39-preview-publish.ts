import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

function loadDotEnv() {
  if (!existsSync(".env")) {
    return;
  }

  for (const line of readFileSync(".env", "utf-8").replace(/\r/g, "").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    let value = trimmed.slice(separatorIndex + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    process.env[key] ??= value;
  }
}

async function main() {
  loadDotEnv();
  const { prisma } = await import("../lib/prisma");

  const suffix = Date.now();
  const user = await prisma.user.upsert({
    where: { email: "v39-preview-publish@example.com" },
    update: {},
    create: {
      email: "v39-preview-publish@example.com",
      passwordHash: "verify-only",
      displayName: "V3.9 验证用户",
    },
  });

  const game = await prisma.game.create({
    data: {
      authorId: user.id,
      title: `V3.9 预览发布验证 ${suffix}`,
      description: "用于验证草稿预览、发布状态更新和首页可见性的临时游戏。",
      tags: ["v3.9", "preview", "publish"],
      status: "DRAFT",
      versions: {
        create: {
          version: 1,
          manifestUrl: `http://localhost:9000/yaha-games/verify/${suffix}/manifest.json`,
          entryUrl: `http://localhost:9000/yaha-games/verify/${suffix}/index.html`,
          artifactBaseUrl: `http://localhost:9000/yaha-games/verify/${suffix}`,
          entryFile: "index.html",
          runtime: "iframe-html-v1",
        },
      },
    },
    include: { versions: true },
  });

  const version = game.versions[0];
  assert(version, "验证游戏应创建一个版本");

  await prisma.game.update({
    where: { id: game.id },
    data: { latestVersionId: version.id },
  });

  const homeBeforePublish = await prisma.game.findMany({ where: { status: "PUBLISHED", id: game.id } });
  assert.equal(homeBeforePublish.length, 0, "草稿不应出现在 Home published 查询中");

  const published = await prisma.game.update({
    where: { id: game.id },
    data: { status: "PUBLISHED", publishedAt: new Date() },
  });
  assert.equal(published.status, "PUBLISHED", "发布应更新 games.status = PUBLISHED");

  const homeAfterPublish = await prisma.game.findMany({ where: { status: "PUBLISHED", id: game.id } });
  assert.equal(homeAfterPublish.length, 1, "发布后应能被 Home published 查询命中");

  await prisma.game.delete({ where: { id: game.id } });

  console.log("V3.9 preview/publish DB verification passed", {
    gameId: game.id,
    versionId: version.id,
  });

  await prisma.$disconnect();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
