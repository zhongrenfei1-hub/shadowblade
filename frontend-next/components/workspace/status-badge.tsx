import { Badge, type BadgeProps } from "@/components/ui/badge";
import { STATUS_LABEL, type Status } from "@/lib/api";

export function StatusBadge({ status }: { status: Status }) {
  return <Badge variant={status as BadgeProps["variant"]}>{STATUS_LABEL[status]}</Badge>;
}
