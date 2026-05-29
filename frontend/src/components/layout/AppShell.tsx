"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ElementType, ReactNode } from "react";
import {
  Bell,
  CircleHelp,
  Database,
  Download,
  FileText,
  Layers,
  Map,
  Plus,
  Radar,
  Satellite,
  Search,
  Settings,
  BarChart3,
  Brain
} from "lucide-react";

import { listAssessments } from "@/lib/api";
import type { Assessment } from "@/lib/types";

const navItems = [
  { href: "/", label: "Workspace" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/history", label: "History" },
  { href: "/reports", label: "Reports" }
];

const toolItems = [
  { label: "Map Layers", icon: Layers },
  { label: "AI Tools", icon: Brain },
  { label: "Analysis", icon: BarChart3, active: true },
  { label: "Imagery", icon: Satellite },
  { label: "Export", icon: Download }
];

type Props = {
  children: ReactNode;
  sidebar?: boolean;
};

export function AppShell({ children, sidebar = true }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [activePanel, setActivePanel] = useState<"notifications" | "help" | "profile" | "search" | null>(null);
  const [globalSearch, setGlobalSearch] = useState("");
  const [assessments, setAssessments] = useState<Assessment[]>([]);

  useEffect(() => {
    void listAssessments().then(setAssessments);
  }, []);

  const searchResults = useMemo(() => {
    const needle = globalSearch.trim().toLowerCase();
    if (needle.length < 2) return [];
    return assessments
      .filter((item) => `${item.name} ${item.location_name} ${item.assessment_id}`.toLowerCase().includes(needle))
      .slice(0, 5);
  }, [assessments, globalSearch]);

  function submitSearch() {
    const query = globalSearch.trim();
    if (!query) return;
    router.push(`/history?search=${encodeURIComponent(query)}`);
    setActivePanel(null);
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <header className="relative flex h-16 items-center justify-between border-b border-outline-variant bg-surface px-5">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2 text-headline-md font-bold text-primary">
            <Map className="h-5 w-5" />
            CrisisMap
          </Link>
          <nav className="hidden items-center gap-7 md:flex">
            {navItems.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex h-16 items-center border-b-2 text-headline-sm transition-colors ${
                    active ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-primary"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="hidden items-center gap-4 md:flex">
          <label className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
            <input
              value={globalSearch}
              onChange={(event) => {
                setGlobalSearch(event.target.value);
                setActivePanel(event.target.value.trim().length >= 2 ? "search" : null);
              }}
              onFocus={() => setActivePanel(globalSearch.trim().length >= 2 ? "search" : activePanel)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitSearch();
                if (event.key === "Escape") setActivePanel(null);
              }}
              className="w-72 rounded border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-body-sm focus:border-primary focus:outline-none"
              placeholder="Search operational data..."
            />
          </label>
          <IconButton icon={Bell} label="Notifications" active={activePanel === "notifications"} onClick={() => setActivePanel((current) => (current === "notifications" ? null : "notifications"))} />
          <Link href="/settings">
            <IconButton icon={Settings} label="Settings" active={pathname.startsWith("/settings")} />
          </Link>
          <IconButton icon={CircleHelp} label="Help" active={activePanel === "help"} onClick={() => setActivePanel((current) => (current === "help" ? null : "help"))} />
          <button
            aria-label="User profile"
            onClick={() => setActivePanel((current) => (current === "profile" ? null : "profile"))}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-container font-mono text-label-mono text-on-primary"
          >
            CM
          </button>
        </div>
        <div className="flex items-center gap-4 md:hidden">
          <IconButton icon={Bell} label="Notifications" active={activePanel === "notifications"} onClick={() => setActivePanel((current) => (current === "notifications" ? null : "notifications"))} />
          <Link href="/settings">
            <IconButton icon={Settings} label="Settings" active={pathname.startsWith("/settings")} />
          </Link>
        </div>
        {activePanel ? (
          <div className="absolute right-5 top-14 z-[800] w-80 rounded-lg border border-outline-variant bg-white p-4 shadow-panel">
            {activePanel === "search" ? (
              <SearchPanel results={searchResults} query={globalSearch} onSubmit={submitSearch} />
            ) : activePanel === "profile" ? (
              <ProfilePanel />
            ) : (
              <>
                <h2 className="font-mono text-label-mono uppercase text-primary">{activePanel === "notifications" ? "Notifications" : "Help"}</h2>
                <p className="mt-2 text-body-sm text-on-surface-variant">
                  {activePanel === "notifications"
                    ? "No new operational alerts. Current demo assessment is available for review."
                    : "Use Workspace to run a demo assessment, Dashboard to filter damage layers, and Reports to export artifacts."}
                </p>
                {activePanel === "notifications" ? (
                  <Link href="/history" className="mt-4 block rounded bg-primary px-3 py-2 text-center font-mono text-label-mono uppercase text-on-primary">
                    Open History
                  </Link>
                ) : null}
              </>
            )}
          </div>
        ) : null}
      </header>

      <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
        {sidebar ? <OperationalSidebar /> : null}
        <main className="min-w-0 flex-1 overflow-hidden">{children}</main>
      </div>

      <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-outline-variant bg-surface-container-lowest md:hidden">
        {navItems.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} className={active ? "text-primary" : "text-on-surface-variant"}>
              <span className="font-mono text-[10px] uppercase">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function IconButton({ icon: Icon, label, active = false, onClick }: { icon: ElementType; label: string; active?: boolean; onClick?: () => void }) {
  return (
    <button
      aria-label={label}
      onClick={onClick}
      className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors ${
        active ? "bg-surface-container-high text-primary" : "text-on-surface-variant hover:bg-surface-container-high"
      }`}
    >
      <Icon className="h-5 w-5" />
    </button>
  );
}

function OperationalSidebar() {
  const [activeTool, setActiveTool] = useState("Analysis");
  const [latestAssessment, setLatestAssessment] = useState<Assessment | null>(null);

  useEffect(() => {
    void listAssessments().then((items) => {
      setLatestAssessment(items[items.length - 1] ?? null);
    });
  }, []);

  return (
    <aside className="hidden h-full w-[280px] shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest p-4 lg:flex xl:w-panel-width">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded bg-primary-container/20 text-primary">
          <Radar className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-headline-sm text-primary">Active Job</h2>
          <p className="font-mono text-label-mono text-on-surface-variant">
            {latestAssessment ? `${latestAssessment.assessment_id} - ${latestAssessment.progress}% ${latestAssessment.status}` : "No active assessment"}
          </p>
        </div>
      </div>
      <Link
        href="/"
        className="mb-5 flex items-center justify-center gap-2 rounded bg-primary px-4 py-3 text-headline-sm text-on-primary hover:bg-primary-container"
      >
        <Plus className="h-5 w-5" />
        New Assessment
      </Link>
      <div className="space-y-2 border-t border-outline-variant pt-5">
        {toolItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              onClick={() => setActiveTool(item.label)}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 font-mono text-label-mono uppercase transition-all ${
                activeTool === item.label
                  ? "bg-secondary-container font-bold text-on-secondary-container"
                  : "text-on-surface-variant hover:bg-surface-container"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </button>
          );
        })}
      </div>
      <ToolPanel activeTool={activeTool} latestAssessment={latestAssessment} />
      <div className="mt-auto space-y-2 border-t border-outline-variant pt-5">
        <Link href="/settings" className="flex items-center gap-3 rounded px-3 py-2 font-mono text-label-mono uppercase text-on-surface-variant">
          <Database className="h-4 w-4" />
          System
        </Link>
        <Link href="/docs" className="flex items-center gap-3 rounded px-3 py-2 font-mono text-label-mono uppercase text-on-surface-variant">
          <FileText className="h-4 w-4" />
          Documentation
        </Link>
      </div>
    </aside>
  );
}

function SearchPanel({ results, query, onSubmit }: { results: Assessment[]; query: string; onSubmit: () => void }) {
  return (
    <div>
      <h2 className="font-mono text-label-mono uppercase text-primary">Search Results</h2>
      {results.length ? (
        <div className="mt-3 space-y-2">
          {results.map((item) => (
            <Link key={item.assessment_id} href={`/dashboard?assessment=${item.assessment_id}`} className="block rounded border border-outline-variant p-3 hover:border-primary">
              <p className="text-body-sm font-semibold">{item.name}</p>
              <p className="font-mono text-label-mono text-on-surface-variant">{item.assessment_id} - {item.location_name}</p>
            </Link>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-body-sm text-on-surface-variant">No direct match for "{query}".</p>
      )}
      <button onClick={onSubmit} className="mt-4 w-full rounded bg-primary px-3 py-2 font-mono text-label-mono uppercase text-on-primary">
        Search History
      </button>
    </div>
  );
}

function ProfilePanel() {
  return (
    <div>
      <h2 className="font-mono text-label-mono uppercase text-primary">User Profile</h2>
      <p className="mt-2 text-body-sm font-semibold">CrisisMap Operator</p>
      <p className="font-mono text-label-mono text-on-surface-variant">Demo workspace - Admin</p>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <Link href="/settings" className="rounded border border-outline-variant px-3 py-2 text-center font-mono text-label-mono uppercase">
          Settings
        </Link>
        <Link href="/docs" className="rounded border border-outline-variant px-3 py-2 text-center font-mono text-label-mono uppercase">
          Docs
        </Link>
      </div>
    </div>
  );
}

function ToolPanel({ activeTool, latestAssessment }: { activeTool: string; latestAssessment: Assessment | null }) {
  const content = {
    "Map Layers": ["Buildings, medical, utilities, roads, and population overlays are controlled from the Dashboard panel.", "/dashboard"],
    "AI Tools": ["TokenRouter model routing and confidence thresholds are configured from Settings.", "/settings"],
    Analysis: [latestAssessment ? `Latest assessment ${latestAssessment.assessment_id} is ${latestAssessment.status}.` : "Run a new analysis from Workspace.", latestAssessment ? `/dashboard?assessment=${latestAssessment.assessment_id}` : "/"],
    Imagery: ["Before/after imagery ranges are set from the Workspace temporal controls.", "/"],
    Export: ["PDF, DOCX, and GeoJSON exports are available from Reports.", "/reports"]
  }[activeTool] ?? ["Select a tool to inspect available actions.", "/"];

  return (
    <div className="mt-4 rounded border border-outline-variant bg-surface p-3">
      <p className="font-mono text-label-mono uppercase text-primary">{activeTool}</p>
      <p className="mt-1 text-body-sm text-on-surface-variant">{content[0]}</p>
      <Link href={content[1]} className="mt-3 block rounded bg-surface-container px-3 py-2 text-center font-mono text-label-mono uppercase text-primary">
        Open
      </Link>
    </div>
  );
}
