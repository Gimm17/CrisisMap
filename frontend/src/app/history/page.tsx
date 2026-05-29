"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarDays, ChevronLeft, ChevronRight, Filter, RefreshCw, Search } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { createAssessment, listAssessments } from "@/lib/api";
import { demoAssessment } from "@/lib/demo";
import { formatDateTime } from "@/lib/format";
import type { Assessment, AssessmentStatus } from "@/lib/types";

export default function HistoryPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([demoAssessment]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AssessmentStatus | "all">("all");
  const [dateRange, setDateRange] = useState<"30" | "all">("30");
  const [page, setPage] = useState(1);
  const [rerunState, setRerunState] = useState<string | null>(null);
  const pageSize = 5;

  useEffect(() => {
    void listAssessments().then(setAssessments);
  }, []);

  useEffect(() => {
    setSearch(new URLSearchParams(window.location.search).get("search") ?? "");
  }, []);

  const rows = useMemo(() => {
    const baseRows = [
      ...assessments,
      {
        ...demoAssessment,
        assessment_id: "ASM-828",
        name: "Haiti SW Region Scan",
        location_name: "Les Cayes, Haiti",
        status: "running" as const,
        progress: 45,
        runtime_seconds: null
      },
      {
        ...demoAssessment,
        assessment_id: "ASM-821",
        name: "Khartoum Infrastructure",
        location_name: "Khartoum, Sudan",
        status: "failed" as const,
        progress: 0,
        runtime_seconds: 134
      }
    ];
    const needle = search.toLowerCase();
    const now = Date.now();
    const maxAgeMs = 30 * 24 * 60 * 60 * 1000;
    return baseRows.filter((row) => {
      const searchMatch = !needle || row.name.toLowerCase().includes(needle) || row.location_name.toLowerCase().includes(needle) || row.assessment_id.toLowerCase().includes(needle);
      const statusMatch = statusFilter === "all" || row.status === statusFilter;
      const dateMatch = dateRange === "all" || now - new Date(row.created_at).getTime() <= maxAgeMs;
      return searchMatch && statusMatch && dateMatch;
    });
  }, [assessments, dateRange, search, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const visibleRows = rows.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const pageButtons = Array.from({ length: pageCount }, (_, index) => index + 1).slice(0, 5);

  useEffect(() => {
    setPage(1);
  }, [dateRange, search, statusFilter]);

  async function rerun(row: Assessment) {
    setRerunState(row.assessment_id);
    try {
      const next = await createAssessment({ mode: row.mode, name: `${row.name} Re-run`, location_name: row.location_name });
      setAssessments((current) => [next, ...current]);
    } catch {
      setAssessments((current) => current);
    } finally {
      setRerunState(null);
    }
  }

  return (
    <AppShell>
      <div className="h-full overflow-y-auto p-8 pb-24">
        <div className="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h1 className="text-headline-lg">Operational History</h1>
            <p className="mt-2 text-body-md text-on-surface-variant">Review past assessments, model outputs, and export datasets.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} className="w-80 rounded border border-outline-variant bg-white py-2 pl-9 pr-3 text-body-sm" placeholder="Filter by location or ID..." />
            </label>
            <button
              onClick={() => setDateRange((value) => (value === "30" ? "all" : "30"))}
              className="flex items-center gap-2 rounded border border-outline-variant bg-white px-4 py-2 font-mono text-label-mono uppercase"
            >
              <CalendarDays className="h-4 w-4" />
              {dateRange === "30" ? "Last 30 Days" : "All Dates"}
            </button>
            <label className="flex items-center gap-2 rounded border border-outline-variant bg-white px-4 py-2 font-mono text-label-mono uppercase">
              <Filter className="h-4 w-4" />
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as AssessmentStatus | "all")} className="bg-transparent outline-none">
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="running">Running</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </select>
            </label>
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border border-outline-variant bg-white shadow-panel">
          <table className="w-full border-collapse text-left">
            <thead className="font-mono text-label-mono uppercase">
              <tr className="border-b border-outline-variant">
                <th className="p-5">Assessment Name</th>
                <th className="p-5">Location</th>
                <th className="p-5">Status</th>
                <th className="p-5">Created Date</th>
                <th className="p-5">Runtime</th>
                <th className="p-5">AI Model</th>
                <th className="p-5">Pipeline</th>
                <th className="p-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.assessment_id} className="border-b border-outline-variant even:bg-surface">
                  <td className="p-5">
                    <div className="text-headline-sm">{row.name}</div>
                    <div className="font-mono text-label-mono text-on-surface-variant">ID: {row.assessment_id}</div>
                  </td>
                  <td className="p-5 text-body-md">{row.location_name}</td>
                  <td className="p-5">
                    <Status status={row.status} />
                  </td>
                  <td className="p-5 text-body-md">{formatDateTime(row.created_at)}</td>
                  <td className="p-5 text-body-md">{row.runtime_seconds ? `${row.runtime_seconds}s` : "--"}</td>
                  <td className="p-5 text-body-md">{row.tokenrouter?.model ?? "pending"}</td>
                  <td className="p-5 font-mono text-label-mono uppercase text-on-surface-variant">{String(row.pipeline?.method ?? "pending")}</td>
                  <td className="p-5">
                    <div className="flex justify-end gap-2">
                      <button aria-label={`Re-run ${row.name}`} onClick={() => void rerun(row)} className="rounded p-2 text-on-surface-variant hover:bg-surface-container">
                        <RefreshCw className={`h-4 w-4 ${rerunState === row.assessment_id ? "animate-spin" : ""}`} />
                      </button>
                      {row.status === "completed" ? (
                        <Link href={`/dashboard?assessment=${row.assessment_id}`} className="rounded bg-primary-container px-3 py-2 font-mono text-label-mono uppercase text-on-primary">
                          Open Result
                        </Link>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between bg-surface p-5 text-body-sm">
            <span>
              Showing {rows.length ? (currentPage - 1) * pageSize + 1 : 0} to {Math.min(currentPage * pageSize, rows.length)} of {rows.length} entries
            </span>
            <div className="flex gap-2 font-mono">
              <button
                aria-label="Previous history page"
                disabled={currentPage <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                className="flex h-8 w-8 items-center justify-center rounded disabled:opacity-40 hover:bg-surface-container"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              {pageButtons.map((item) => (
                <button
                  key={item}
                  onClick={() => setPage(item)}
                  className={`h-8 w-8 rounded disabled:opacity-40 ${currentPage === item ? "bg-primary text-on-primary" : "hover:bg-surface-container"}`}
                >
                  {item}
                </button>
              ))}
              <button
                aria-label="Next history page"
                disabled={currentPage >= pageCount}
                onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
                className="flex h-8 w-8 items-center justify-center rounded disabled:opacity-40 hover:bg-surface-container"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function Status({ status }: { status: Assessment["status"] }) {
  const cls = {
    completed: "bg-status-intact/15 text-status-intact border-status-intact/30",
    running: "bg-secondary-container text-on-secondary-container border-secondary-container",
    failed: "bg-red-50 text-status-destroyed border-red-200",
    pending: "bg-surface-container text-on-surface-variant border-outline-variant"
  }[status];
  return <span className={`rounded border px-2 py-1 font-mono text-[11px] uppercase ${cls}`}>{status}</span>;
}
