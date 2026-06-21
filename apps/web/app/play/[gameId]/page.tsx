import { PlayClient } from "./play-client";
import { getCurrentUser } from "@/lib/auth";

type PlayPageProps = {
  params: Promise<{
    gameId: string;
  }>;
  searchParams: Promise<{
    preview?: string;
  }>;
};

export default async function PlayPage({ params, searchParams }: PlayPageProps) {
  const { gameId } = await params;
  const { preview } = await searchParams;
  const user = await getCurrentUser();

  return <PlayClient gameId={gameId} preview={preview === "1"} user={user} />;
}
