import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "Yaha - AI 互动游戏平台",
  description: "用自然语言和 AI Agent 协作生成可发布的互动小游戏",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
