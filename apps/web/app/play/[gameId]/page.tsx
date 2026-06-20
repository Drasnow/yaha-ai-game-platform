import { PlayClient } from "./play-client";

type PlayPageProps = {
  params: Promise<{
    gameId: string;
  }>;
};

export default async function PlayPage({ params }: PlayPageProps) {
  const { gameId } = await params;

  return <PlayClient gameId={gameId} />;
}