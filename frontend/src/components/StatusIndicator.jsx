function StatusIndicator({ status, onRetry }) {
  const label =
    status === "ready"
      ? "Ready"
      : status === "checking"
        ? "Checking..."
        : status === "degraded"
          ? "Unavailable"
          : "Unavailable";

  return (
    <div className={`status-indicator status-${status}`} aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      <span>{label}</span>
      {status !== "ready" && status !== "checking" ? (
        <button type="button" className="status-retry" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export default StatusIndicator;
