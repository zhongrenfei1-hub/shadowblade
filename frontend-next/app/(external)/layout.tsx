/** 外部 / 公开访客 layout · 不带 sidebar 和 topbar。
 *  用于：分享链接 /share/[token]、登录页、状态页等无身份场景。
 *  用 <main> 充当唯一 landmark — 屏幕阅读器在无 sidebar / skip-link 时仍能定位主内容。 */
export default function ExternalLayout({ children }: { children: React.ReactNode }) {
  return <main id="main-content" className="min-h-screen">{children}</main>;
}
