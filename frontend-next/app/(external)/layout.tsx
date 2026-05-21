/** 外部 / 公开访客 layout · 不带 sidebar 和 topbar。
 *  用于：分享链接 /share/[token]、登录页、状态页等无身份场景。 */
export default function ExternalLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen">{children}</div>;
}
