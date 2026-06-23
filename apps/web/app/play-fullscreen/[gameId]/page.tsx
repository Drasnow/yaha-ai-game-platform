import { FullscreenClient } from "./fullscreen-client";

type PlayFullscreenPageProps = {
  params: Promise<{
    gameId: string;
  }>;
  searchParams: Promise<{
    preview?: string;
  }>;
};

export default async function PlayFullscreenPage({ params, searchParams }: PlayFullscreenPageProps) {
  const { gameId } = await params;
  const { preview } = await searchParams;

  return <FullscreenClient gameId={gameId} preview={preview === "1"} />;
}
