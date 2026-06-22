import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const adapter = new PrismaPg({
  connectionString: process.env.DATABASE_URL,
});

const prisma = new PrismaClient({ adapter });

const demoUser = {
  email: "demo@yaha.local",
  password: "YahaDemo123!",
  displayName: "Demo Creator",
};

const seedGames = [
  {
    title: "星际点击挑战",
    description: "玩家需要在倒计时内点击不断出现的能量核心，积累分数并挑战反应速度。",
    tags: ["click", "arcade", "反应力"],
    coverUrl: null,
    artifactBaseUrl: "http://localhost:9000/yaha-games/games/seed/sample-click-challenge/v1",
  },
  {
    title: "AI 知识问答冒险",
    description: "以太空探索为主题的问答小游戏，玩家通过回答问题推进剧情并解锁下一关。",
    tags: ["quiz", "story", "知识问答"],
    coverUrl: null,
    artifactBaseUrl: "http://localhost:9000/yaha-games/games/seed/sample-quiz-adventure/v1",
  },
  {
    // 第三个游戏：来自 AI Create 流程生成并发布的真实案例
    // 该游戏通过 /create 页面触发生成，对应 task_id: cmqo12wdr000vkgw9m1he0oen
    title: "躲避障碍",
    description: "驾驶霓虹侦察艇在失控陨石雨与太空残骸中穿梭闪避，坚持越久分数越高。用方向键在有限空间内移动，冲向安全星门。",
    tags: ["霓虹科幻", "躲避生存", "高分挑战", "紧张刺激"],
    coverUrl: null,
    artifactBaseUrl: "http://localhost:9000/yaha-games/games/generated/cmqo12wdr000vkgw9m1he0oen/v1",
  },
];

async function upsertPublishedGame(userId: string, game: (typeof seedGames)[number]) {
  const existing = await prisma.game.findFirst({
    where: { authorId: userId, title: game.title },
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

  if (!existing) {
    const created = await prisma.game.create({
      data: {
        authorId: userId,
        title: game.title,
        description: game.description,
        coverUrl: game.coverUrl,
        tags: game.tags,
        status: "PUBLISHED",
        publishedAt: new Date(),
        versions: {
          create: {
            version: 1,
            manifestUrl: `${game.artifactBaseUrl}/manifest.json`,
            entryUrl: `${game.artifactBaseUrl}/index.html`,
            artifactBaseUrl: game.artifactBaseUrl,
            entryFile: "index.html",
            runtime: "iframe-html-v1",
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

    const versionId = created.versions[0]?.id;
    if (versionId) {
      await prisma.game.update({ where: { id: created.id }, data: { latestVersionId: versionId } });
    }
    return created.id;
  }

  let versionId = existing.latestVersionId ?? existing.versions[0]?.id;
  if (!versionId) {
    const version = await prisma.gameVersion.create({
      data: {
        gameId: existing.id,
        version: 1,
        manifestUrl: `${game.artifactBaseUrl}/manifest.json`,
        entryUrl: `${game.artifactBaseUrl}/index.html`,
        artifactBaseUrl: game.artifactBaseUrl,
        entryFile: "index.html",
        runtime: "iframe-html-v1",
      },
      select: { id: true },
    });
    versionId = version.id;
  }

  await prisma.game.update({
    where: { id: existing.id },
    data: {
      description: game.description,
      coverUrl: game.coverUrl,
      tags: game.tags,
      status: "PUBLISHED",
      latestVersionId: versionId,
      publishedAt: new Date(),
    },
  });

  return existing.id;
}

async function main() {
  const passwordHash = await bcrypt.hash(demoUser.password, 10);
  const user = await prisma.user.upsert({
    where: { email: demoUser.email },
    update: { displayName: demoUser.displayName, passwordHash },
    create: { email: demoUser.email, displayName: demoUser.displayName, passwordHash },
    select: { id: true, email: true },
  });

  const gameIds = [];
  for (const game of seedGames) {
    gameIds.push(await upsertPublishedGame(user.id, game));
  }

  console.log(JSON.stringify({ user: user.email, password: demoUser.password, publishedGames: gameIds.length, gameIds }, null, 2));
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
