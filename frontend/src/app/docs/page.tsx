"use client";

import Link from "next/link";
import { ArrowRight, BookOpen, FileText, History, Map, Settings } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";

const docSections = [
  {
    title: "Workspace",
    body: "Configure AOI, event dates, source readiness, and TokenRouter model before running an assessment.",
    href: "/",
    icon: Map
  },
  {
    title: "Dashboard",
    body: "Review severity overlays, infrastructure filters, priority reconstruction ranking, and AI model metadata.",
    href: "/dashboard",
    icon: BookOpen
  },
  {
    title: "Reports",
    body: "Export donor summaries, GeoJSON layers, and generated PDF/DOCX artifacts.",
    href: "/reports",
    icon: FileText
  },
  {
    title: "Settings",
    body: "Change analysis parameters and server-side TokenRouter model routing.",
    href: "/settings",
    icon: Settings
  },
  {
    title: "History",
    body: "Search, filter, open, and re-run previous operational assessments.",
    href: "/history",
    icon: History
  }
];

export default function DocsPage() {
  return (
    <AppShell>
      <div className="h-full overflow-y-auto p-8 pb-24">
        <div className="max-w-4xl rounded-lg border border-outline-variant bg-white p-8 shadow-panel">
          <h1 className="text-headline-lg text-primary">CrisisMap Documentation</h1>
          <p className="mt-3 text-body-md text-on-surface-variant">
            Operational demo documentation for the Beirut damage assessment workflow.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {docSections.map(({ title, body, href, icon: Icon }) => (
              <Link key={title} href={href} className="group rounded border border-outline-variant bg-surface p-5 transition-colors hover:border-primary hover:bg-surface-container-lowest">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="flex items-center gap-2 text-headline-sm">
                    <Icon className="h-5 w-5 text-primary" />
                    {title}
                  </h2>
                  <ArrowRight className="h-4 w-4 text-on-surface-variant transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                </div>
                <p className="mt-2 text-body-sm text-on-surface-variant">{body}</p>
                <span className="mt-4 inline-block font-mono text-label-mono uppercase text-primary">Open Section</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
