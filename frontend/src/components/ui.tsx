import { useEffect, useRef, type ReactNode } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  X,
} from "lucide-react";
import { errorCopy } from "../api/client";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive" | "risk" | "critical" | "accent";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function Loading({ label = "Reading graph data…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={18} />
      {label}
    </div>
  );
}
export function ErrorNotice({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="notice notice-error" role="alert">
      <AlertCircle size={18} />
      <div>
        <strong>Request unavailable</strong>
        <p>{errorCopy(error)}</p>
        {onRetry && (
          <button className="text-button" onClick={onRetry}>
            Retry request <ArrowRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-mark">
        <span />
        <span />
        <span />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function SectionHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}
export function Pagination({
  total,
  offset,
  size,
  onChange,
  label,
}: {
  total: number;
  offset: number;
  size: number;
  onChange: (offset: number) => void;
  label: string;
}) {
  if (total <= size)
    return (
      <p className="pagination-summary">
        {total} {label}
      </p>
    );
  return (
    <nav className="pagination" aria-label={`${label} pagination`}>
      <span>
        {Math.min(offset + 1, total)}–{Math.min(offset + size, total)} of{" "}
        {total} {label}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label={`Previous ${label}`}
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - size))}
        >
          <ChevronLeft size={16} />
        </button>
        <button
          className="icon-button"
          aria-label={`Next ${label}`}
          disabled={offset + size >= total}
          onClick={() => onChange(offset + size)}
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </nav>
  );
}
export function Modal({
  title,
  subtitle,
  children,
  onClose,
  busy = false,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = `dialog-${title.toLowerCase().replaceAll(/[^a-z]+/g, "-")}`;
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement;
    dialog?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = overflow;
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "modal-wide" : ""}`}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <header className="modal-heading">
        <div>
          <span className="eyebrow">RippleProof workspace</span>
          <h2 id={titleId}>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          disabled={busy}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </header>
      <div className="modal-body">{children}</div>
    </dialog>
  );
}
export function Status({
  value,
}: {
  value: "on_time" | "at_risk" | "insufficient_data";
}) {
  return (
    <Badge
      tone={
        value === "on_time"
          ? "positive"
          : value === "at_risk"
            ? "risk"
            : "neutral"
      }
    >
      {value === "on_time" ? <Check size={12} /> : <AlertCircle size={12} />}
      {value === "on_time"
        ? "Covered"
        : value === "at_risk"
          ? "At risk"
          : "Needs data"}
    </Badge>
  );
}
export function PropertyList({
  properties,
}: {
  properties: Record<string, unknown>;
}) {
  return (
    <dl className="property-list">
      {Object.entries(properties).map(([key, value]) => (
        <div key={key}>
          <dt>{key.replaceAll("_", " ")}</dt>
          <dd>
            {value == null
              ? "Unknown"
              : typeof value === "object"
                ? JSON.stringify(value)
                : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
