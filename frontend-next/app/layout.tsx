import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

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
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://frontend-next-two-lac.vercel.app",
  ),
  title: "ShadowBlade · 企业级 AI 视频云",
  description:
    "ShadowBlade 把一份简报变成可以直接上线的营销 / 培训 / 产品视频，4 分钟出片，对照你的品牌套件渲染。",
  icons: { icon: "/favicon.svg" },
  openGraph: { images: ["/og-image.svg"] },
};

/** 根 layout 只负责 html/body/字体。
 *  应用框架（sidebar + topbar）在 (app)/layout.tsx；
 *  外部分享走 (external)/layout.tsx，不带 sidebar。 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
