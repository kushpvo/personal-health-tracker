import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type Zone = "optimal" | "sufficient" | "out_of_range" | "unknown";

export function zoneColor(zone: Zone): string {
  switch (zone) {
    case "optimal":
      return "#22c55e";
    case "sufficient":
      return "#06b6d4";
    case "out_of_range":
      return "#f97316";
    default:
      return "#6b7280";
  }
}

export function zoneLabel(zone: Zone): string {
  switch (zone) {
    case "optimal":
      return "Optimal";
    case "sufficient":
      return "Sufficient";
    case "out_of_range":
      return "Out of Range";
    default:
      return "Unknown";
  }
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
