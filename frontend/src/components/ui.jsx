/**
 * Shared UI primitives — the single implementation of every repeated
 * visual pattern (cards, buttons, badges, states, tables, modals, forms).
 * Pages compose these instead of re-implementing markup/styles.
 */

import {
  requestStatusLabel,
  requestStatusVariant,
  documentStatusLabel,
  documentStatusVariant,
  travelTypeLabel,
} from "../lib/format.js";

/* ------------------------------------------------------------------ */
/* Card / section                                                      */
/* ------------------------------------------------------------------ */

export function Card({ title, subtitle, actions, children, className = "", padded = true }) {
  return (
    <section className={`card ${padded ? "card-pad" : ""} ${className}`.trim()}>
      {(title || actions) && (
        <div className="flex-between mb-2">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="btn-row">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */

export function Button({
  variant = "primary",
  size,
  block,
  loading = false,
  children,
  className = "",
  type = "button",
  disabled,
  ...rest
}) {
  const classes = [
    "btn",
    `btn--${variant}`,
    size === "sm" && "btn--sm",
    size === "lg" && "btn--lg",
    block && "btn--block",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? "Working…" : children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Badges                                                              */
/* ------------------------------------------------------------------ */

export function Badge({ variant = "neutral", dot = false, children }) {
  return (
    <span className={`badge badge--${variant}`}>
      {dot && <span className="badge-dot" aria-hidden="true" />}
      {children}
    </span>
  );
}

export function RequestStatusBadge({ status }) {
  return (
    <Badge variant={requestStatusVariant(status)} dot>
      {requestStatusLabel(status)}
    </Badge>
  );
}

export function DocumentStatusBadge({ status }) {
  return (
    <Badge variant={documentStatusVariant(status)}>
      {documentStatusLabel(status)}
    </Badge>
  );
}

export function TravelTypeBadge({ type }) {
  const variant = type === "INTERNATIONAL" ? "primary" : "neutral";
  return <Badge variant={variant}>{travelTypeLabel(type)}</Badge>;
}

/* ------------------------------------------------------------------ */
/* States                                                              */
/* ------------------------------------------------------------------ */

export function LoadingState({ label = "Loading…" }) {
  return (
    <div className="state" role="status">
      <div className="spinner" aria-hidden="true" />
      <p className="state-description mb-0">{label}</p>
    </div>
  );
}

export function EmptyState({ icon = "🗂️", title, description, action }) {
  return (
    <div className="state">
      <div className="state-icon" aria-hidden="true">
        {icon}
      </div>
      <p className="state-title">{title}</p>
      {description && <p className="state-description">{description}</p>}
      {action && <div className="btn-row" style={{ justifyContent: "center" }}>{action}</div>}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div className="state" role="alert">
      <div className="state-icon" aria-hidden="true">
        ⚠️
      </div>
      <p className="state-title">{title}</p>
      {message && <p className="state-description">{message}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function InlineError({ children }) {
  if (!children) return null;
  return (
    <div className="alert alert--error" role="alert">
      <span>{children}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Table scaffold                                                      */
/* ------------------------------------------------------------------ */

export function Table({ columns, children, compact = false }) {
  return (
    <div className="table-wrap">
      <table className={`table ${compact ? "table--compact" : ""}`}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} style={column.align === "right" ? { textAlign: "right" } : undefined}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Form fields                                                         */
/* ------------------------------------------------------------------ */

export function FormField({ label, htmlFor, required, error, help, children }) {
  return (
    <div className="form-field">
      <label htmlFor={htmlFor}>
        {label}
        {required && (
          <span className="required-mark" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {help && !error && <p className="field-help">{help}</p>}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tabs                                                                */
/* ------------------------------------------------------------------ */

export function Tabs({ tabs, activeKey, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={activeKey === tab.key}
          className={`tab${activeKey === tab.key ? " active" : ""}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Modal / confirmation                                                */
/* ------------------------------------------------------------------ */

export function Modal({ title, onClose, children, footer }) {
  return (
    <div
      className="modal-scrim"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && onClose) onClose();
      }}
    >
      <div className="modal">
        <div className="modal-header">
          <div className="flex-between">
            <h2>{title}</h2>
            {onClose && (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={onClose}
                aria-label="Close dialog"
              >
                ✕
              </button>
            )}
          </div>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmationDialog({
  title,
  message,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Modal
      title={title}
      onClose={busy ? undefined : onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            onClick={onConfirm}
            loading={busy}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && <p className="mb-0">{message}</p>}
      {children && <div className={message ? "mt-2" : ""}>{children}</div>}
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Page scaffolding                                                    */
/* ------------------------------------------------------------------ */

export function PageHeader({ title, description, actions }) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        <h1>{title}</h1>
        {description && <p className="page-header-description">{description}</p>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}

export function Breadcrumb({ items }) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <span key={`${item.label}-${index}`} className="flex" style={{ gap: 6 }}>
            {index > 0 && <span aria-hidden="true">/</span>}
            {item.to && !isLast ? (
              <a href={item.to}>{item.label}</a>
            ) : (
              <span className={isLast ? "current" : undefined}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function StatCard({ label, value, hint, tone }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${tone ? `kpi-value--${tone}` : ""}`.trim()}>
        {value}
      </div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}
