// WP-011 — NotFound page (catch-all route).
//
// Per the WP Contract: "renders 'No page at this URL. Go to the
// dashboard.' with a link to /".

import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <section data-testid="page-not-found">
      <h1>Not found</h1>
      <p>
        No page at this URL. <Link to="/">Go to the dashboard.</Link>
      </p>
    </section>
  );
}
