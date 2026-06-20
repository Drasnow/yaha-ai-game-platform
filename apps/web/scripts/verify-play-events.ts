import "dotenv/config";

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";

const appBaseUrl = process.env.VERIFY_APP_URL ?? "http://127.0.0.1:4000";
const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter });

async function postPlayEvent(gameId: string, versionId: string, eventType: string) {
  const response = await fetch(`${appBaseUrl}/api/v1/play-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      gameId,
      versionId,
      eventType,
      message: `V2.7 verification ${eventType}`,
      metadata: { source: "scripts/verify-play-events.ts" },
    }),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(`POST ${eventType} failed: ${response.status} ${JSON.stringify(payload)}`);
  }

  return payload as { playEvent: { id: string } };
}

async function main() {
  const game = await prisma.game.findFirst({
    where: { status: "PUBLISHED", latestVersionId: { not: null } },
    orderBy: { publishedAt: "desc" },
    select: {
      id: true,
      title: true,
      playCount: true,
      latestVersionId: true,
    },
  });

  if (!game?.latestVersionId) {
    throw new Error("No published game with latestVersionId found. Run prisma seed and upload sample game first.");
  }

  const eventTypes = ["load_start", "load_success", "load_failed", "play_start"];
  const createdEventIds = [];

  for (const eventType of eventTypes) {
    const result = await postPlayEvent(game.id, game.latestVersionId, eventType);
    createdEventIds.push(result.playEvent.id);
  }

  const createdEvents = await prisma.playEvent.findMany({
    where: { id: { in: createdEventIds } },
    orderBy: { createdAt: "asc" },
    select: {
      id: true,
      gameId: true,
      versionId: true,
      eventType: true,
      message: true,
      createdAt: true,
    },
  });
  const updatedGame = await prisma.game.findUnique({
    where: { id: game.id },
    select: { playCount: true },
  });

  console.log(
    JSON.stringify(
      {
        appBaseUrl,
        game: {
          id: game.id,
          title: game.title,
          versionId: game.latestVersionId,
          playCountBefore: game.playCount,
          playCountAfter: updatedGame?.playCount,
        },
        createdEvents,
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