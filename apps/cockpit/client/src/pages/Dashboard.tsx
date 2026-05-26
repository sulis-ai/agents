// WP-011 — Dashboard placeholder.
//
// WP-012 fleshes this out with the change-card grid + empty state +
// 10-second liveness poll. WP-011 lands the file at the right path
// so the router resolves; the body is a one-line marker.

export function Dashboard() {
  return (
    <section data-testid="page-dashboard">
      <h1>Dashboard</h1>
      <p>Change cards land in WP-012.</p>
    </section>
  );
}
