import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export const metadata: Metadata = {
  title: "ShadowBlade · 企业级 AI 视频云",
  description:
    "ShadowBlade 把一份简报变成可以直接上线的营销 / 培训 / 产品视频，4 分钟出片，对照你的品牌套件渲染。",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <div className="grid min-h-screen grid-cols-[248px_1fr]">
          <Sidebar />
          <div className="grid grid-rows-[60px_1fr] min-w-0">
            <Topbar />
            <main className="grid content-start gap-8 px-10 py-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
