import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans-google",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono-google",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ShadowBlade · 企业级 AI 视频云",
  description:
    "ShadowBlade 把一份简报变成可以直接上线的营销 / 培训 / 产品视频，4 分钟出片，对照你的品牌套件渲染。",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <div className="grid min-h-screen grid-cols-1 md:grid-cols-[248px_1fr]">
          <Sidebar />
          <div className="grid grid-rows-[60px_1fr] min-w-0">
            <Topbar />
            <main className="grid content-start gap-6 px-4 py-6 md:gap-8 md:px-10 md:py-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
