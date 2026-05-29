"use client";

import { useEffect, useState } from "react";
import type { ElementType } from "react";
import Link from "next/link";
import { Braces, Building2, CheckCircle2, FileDown, FileText, Group, MapPin, MemoryStick, TriangleAlert } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { API_BASE_URL, getAssessment, getReport } from "@/lib/api";
import { demoAssessment, demoReport } from "@/lib/demo";
import { formatNumber } from "@/lib/format";
import type { Assessment, AssessmentReport } from "@/lib/types";

export default function ReportsPage() {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment>(demoAssessment);
  const [report, setReport] = useState<AssessmentReport>(demoReport);

  useEffect(() => {
    setAssessmentId(new URLSearchParams(window.location.search).get("assessment") ?? "demo");
  }, []);

  useEffect(() => {
    if (!assessmentId) return;
    let active = true;
    const id = assessmentId;
    async function loadReportData() {
      const [nextAssessment, nextReport] = await Promise.all([getAssessment(id), getReport(id)]);
      if (!active) return;
      setAssessment(nextAssessment);
      setReport(nextReport);
    }
    void loadReportData();
    return () => {
      active = false;
    };
  }, [assessmentId]);

  return (
    <AppShell sidebar={false}>
      <div className="h-full overflow-y-auto bg-surface p-6 pb-24">
        <article className="mx-auto max-w-5xl overflow-hidden rounded-lg border border-border-muted bg-surface-container-lowest shadow-panel">
          <header className="flex flex-col gap-6 border-b border-border-muted bg-surface p-8 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="mb-4 flex items-center gap-2 font-mono text-label-mono uppercase text-on-surface-variant">
                <MapPin className="h-4 w-4" />
                {assessment.location_name}
                <span>-</span>
                Generated Today
              </div>
              <h1 className="text-headline-lg text-primary">{assessment.name}</h1>
              <p className="mt-2 max-w-2xl text-body-md text-on-surface-variant">
                Comprehensive post-incident structural integrity and humanitarian impact analysis. Prepared for strategic donor allocation and immediate response planning.
              </p>
            </div>
            <div className="flex gap-2">
              <ExportButton icon={FileDown} label="PDF" href={`${API_BASE_URL}/assessments/${assessment.assessment_id}/exports/pdf`} />
              <ExportButton icon={FileText} label="DOCX" href={`${API_BASE_URL}/assessments/${assessment.assessment_id}/exports/docx`} />
              <ExportButton icon={Braces} label="GeoJSON" href={`${API_BASE_URL}/assessments/${assessment.assessment_id}/exports/geojson`} primary />
            </div>
          </header>

          <div className="space-y-9 p-8">
            <section className="grid gap-6 md:grid-cols-[1fr_300px]">
              <div className="rounded border border-outline-variant bg-surface p-6">
                <h2 className="mb-4 flex items-center gap-2 text-headline-md text-primary">
                  <FileText className="h-5 w-5" />
                  Donor Summary
                </h2>
                <p className="whitespace-pre-line text-body-md leading-7">{report.donor_summary}</p>
                <p className="mt-4 text-body-md leading-7">{report.damage_overview}</p>
              </div>
              <div className="space-y-4">
                <ReportStat icon={Building2} label="Buildings Assessed" value={formatNumber(assessment.summary?.buildings_assessed ?? 1420)} />
                <ReportStat icon={TriangleAlert} label="Total Damage Score" value={`${assessment.summary?.total_damage_score ?? 84.2}/100`} danger />
                <ReportStat icon={Group} label="Population Impacted" value={`~${formatNumber(assessment.summary?.estimated_population_impact ?? 155000)}`} />
              </div>
            </section>

            <section>
              <h2 className="mb-4 border-b border-border-muted pb-3 text-headline-md text-primary">Top Reconstruction Priorities</h2>
              <div className="overflow-hidden rounded border border-outline-variant">
                <table className="w-full border-collapse text-left text-body-sm">
                  <thead className="bg-surface-container-high font-mono text-label-mono uppercase">
                    <tr>
                      <th className="p-4">Rank</th>
                      <th className="p-4">Entity ID / Name</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Est. Cost</th>
                      <th className="p-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.priority_buildings.slice(0, 3).map((priority) => (
                      <tr key={priority.building_id} className="border-t border-outline-variant bg-surface">
                        <td className="p-4 font-mono">#{priority.rank}</td>
                        <td className="p-4">
                          <div className="font-semibold text-primary">{priority.name}</div>
                          <div className="font-mono text-label-mono text-on-surface-variant">{priority.building_id}</div>
                        </td>
                        <td className="p-4 text-status-severe">{priority.status}</td>
                        <td className="p-4">${(priority.estimated_cost_usd / 1000000).toFixed(1)}M</td>
                        <td className="p-4 text-right">
                          <Link href={`/priority/${priority.building_id}?assessment=${assessment.assessment_id}`} className="font-mono text-xs uppercase text-primary">
                            View Details
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="mb-4 border-b border-border-muted pb-3 text-headline-md text-primary">Phased Reconstruction Plan</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {report.phased_plan.map((phase, index) => (
                  <div key={phase.phase} className="rounded border border-outline-variant bg-surface p-5" style={{ borderTop: `4px solid ${["#DC2626", "#EA580C", "#F59E0B"][index]}` }}>
                    <h3 className="text-headline-sm">{phase.phase}</h3>
                    <p className="mb-4 font-mono text-label-mono uppercase text-status-severe">{phase.label}</p>
                    <ul className="space-y-3 text-body-sm">
                      {phase.actions.map((action) => (
                        <li key={action} className="flex gap-2">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-on-surface-variant" />
                          {action}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section className="flex gap-5 rounded border border-outline-variant bg-surface p-6">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-secondary-container text-primary">
                <MemoryStick className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-headline-sm text-primary">Engineering & AI Notes</h2>
                <p className="mt-2 text-body-sm text-on-surface-variant">{report.engineering_notes}</p>
                <p className="mt-2 font-mono text-label-mono text-on-surface-variant">
                  Provider: {report.tokenrouter.provider} - Model: {report.tokenrouter.model}
                </p>
              </div>
            </section>
          </div>
          <footer className="bg-surface-container p-6 text-center font-mono text-label-mono uppercase text-on-surface-variant">
            CrisisMap Intelligence Report - Confidential
          </footer>
        </article>
      </div>
    </AppShell>
  );
}

function ExportButton({ icon: Icon, label, href, primary = false }: { icon: ElementType; label: string; href: string; primary?: boolean }) {
  return (
    <a href={href} className={`flex items-center gap-2 rounded border px-4 py-2 font-mono text-label-mono uppercase ${primary ? "border-primary bg-primary text-on-primary" : "border-outline-variant bg-surface text-primary"}`}>
      <Icon className="h-4 w-4" />
      {label}
    </a>
  );
}

function ReportStat({ icon: Icon, label, value, danger = false }: { icon: ElementType; label: string; value: string; danger?: boolean }) {
  return (
    <div className={`relative rounded border ${danger ? "border-status-severe bg-status-severe/15" : "border-outline-variant bg-surface"} p-5`}>
      <h3 className={`font-mono text-label-mono uppercase ${danger ? "text-status-severe" : "text-on-surface-variant"}`}>{label}</h3>
      <p className={`mt-2 text-stat-value ${danger ? "text-status-severe" : "text-primary"}`}>{value}</p>
      <Icon className="absolute right-4 top-1/2 h-9 w-9 -translate-y-1/2 opacity-20" />
    </div>
  );
}
