import React from "react";

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  highlight?: "gold" | "jade" | "danger" | "none";
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  className = "",
  bodyClassName = "",
  highlight = "none",
}) => {
  let borderHighlight = "1px solid var(--color-border)";
  if (highlight === "gold") borderHighlight = "1px solid var(--color-gold)";
  if (highlight === "jade") borderHighlight = "1px solid var(--color-jade)";
  if (highlight === "danger") borderHighlight = "1px solid var(--color-danger)";

  return (
    <div
      className={`rounded-xl transition-all ${className}`}
      style={{
        background: "var(--color-surface-card)",
        border: borderHighlight,
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {(title || action) && (
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          <div>
            {title && (
              <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[var(--color-text-dim)] mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>{children}</div>
    </div>
  );
};
