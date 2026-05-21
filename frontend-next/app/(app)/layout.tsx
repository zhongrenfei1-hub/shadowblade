import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

/** 应用框架 layout · 带 sidebar + topbar。
 *  所有需要登录身份的 page 都进这个 route group。 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[248px_1fr]">
      <Sidebar />
      <div className="grid grid-rows-[60px_1fr] min-w-0">
        <Topbar />
        <main className="grid content-start gap-6 px-4 py-6 md:gap-8 md:px-10 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
