import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ChatProvider } from './providers'
import PageTransition from './PageTransition'
import { FeedbackWidget } from "@/components/FeedbackWidget";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Joy IP 3D - AI图片生成",
  description: "基于AI的3D角色图片生成系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <ChatProvider>
          <PageTransition>{children}</PageTransition>
          <FeedbackWidget />
        </ChatProvider>
      </body>
    </html>
  );
}

