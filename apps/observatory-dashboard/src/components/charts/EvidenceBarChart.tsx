import React from "react";
import type { EvidenceClass } from "../../types/observatory";

interface EvidenceBarChartProps {
  data: Record<EvidenceClass, number>;
  total: number;
}

export const EvidenceBarChart: React.FC<EvidenceBarChartProps> = ({ data, total }) => {
  const categories: { key: EvidenceClass; label: string; color: string; desc: string }[] = [
    {
      key: "infrastructure_observed",
      label: "Infrastructure Observed",
      color: "var(--color-success)",
      desc: "Seam-verified directly by trusted runtime",
    },
    {
      key: "human_authorized",
      label: "Human Authorized",
      color: "var(--color-info)",
      desc: "Independently recorded off-chat human decisions",
    },
    {
      key: "agent_reported",
      label: "Agent Reported (Claimed)",
      color: "var(--color-warning)",
      desc: "Self-asserted claims — never silently trusted",
    },
    {
      key: "unverified",
      label: "Unverified / External",
      color: "var(--color-danger)",
      desc: "Untrusted external inputs with no valid authority",
    },
  ];

  return (
    <div className="space-y-4" role="region" aria-label="Evidence Classification Distribution">
      <div className="flex flex-col gap-3">
        {categories.map((cat) => {
          const count = data[cat.key] || 0;
          const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

          return (
            <div key={cat.key} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--color-text-primary)] flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                    style={{ background: cat.color }}
                    aria-hidden="true"
                  />
                  {cat.label}
                </span>
                <span className="font-mono text-[var(--color-text-dim)]">
                  {count} <span className="opacity-60">({percentage}%)</span>
                </span>
              </div>
              <div
                className="w-full h-2 rounded-full overflow-hidden"
                style={{ background: "rgba(255, 255, 255, 0.08)" }}
                aria-hidden="true"
              >
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${Math.max(percentage, count > 0 ? 3 : 0)}%`,
                    background: cat.color,
                  }}
                />
              </div>
              <p className="text-[11px] text-[var(--color-text-muted)] italic">
                {cat.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Accessible Table for Screen Readers */}
      <table className="sr-only">
        <caption>Evidence Classification Distribution</caption>
        <thead>
          <tr>
            <th scope="col">Evidence Class</th>
            <th scope="col">Count</th>
            <th scope="col">Percentage</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((cat) => (
            <tr key={cat.key}>
              <th scope="row">{cat.label}</th>
              <td>{data[cat.key] || 0}</td>
              <td>{total > 0 ? Math.round(((data[cat.key] || 0) / total) * 100) : 0}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
