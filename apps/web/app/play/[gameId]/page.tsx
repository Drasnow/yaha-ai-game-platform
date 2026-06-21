import { PlayClient } from "./play-client";

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

  return <PlayClient gameId={gameId} preview={preview === "1"} />;
}
