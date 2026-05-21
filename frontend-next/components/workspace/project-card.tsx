import Link from "next/link";
import type { Project } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { StatusBadge } from "./status-badge";
import { relativeTime } from "@/lib/utils";
import { ProjectCover } from "./project-cover";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/projects/${project.id}`} className="group block">
      <Card className="overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-accent-500/40 hover:shadow-lg">
        <div className="relative h-[132px] overflow-hidden">
          <ProjectCover cover={project.cover} />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-navy-950/70" />
          <div className="absolute left-2.5 top-2.5 z-10">
            <StatusBadge status={project.status} />
          </div>
          <div className="absolute bottom-2.5 right-2.5 z-10 rounded border border-border bg-navy-950/65 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            {project.aspect_ratio} · {project.duration_seconds}秒
          </div>
        </div>
        <div className="grid gap-3 p-4">
          <div className="font-semibold leading-snug tracking-tight">{project.name}</div>
          <Progress value={Math.round(project.progress * 100)} className="h-1" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <Avatar className="h-[22px] w-[22px] text-[10px]">
                <AvatarFallback>
                  {project.owner
                    .split(" ")
                    .map((s) => s[0])
                    .join("")
                    .slice(0, 2)}
                </AvatarFallback>
              </Avatar>
              <span>{project.owner}</span>
            </div>
            <span className="num">{relativeTime(project.updated_at)}</span>
          </div>
        </div>
      </Card>
    </Link>
  );
}
