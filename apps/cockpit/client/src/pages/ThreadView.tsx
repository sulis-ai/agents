// WP-011 — ThreadView placeholder.
//
// WP-013/014/015 flesh this out with the header (handle/stage/liveness),
// the tabbed panels (Chat | Files), the file tree, the Monaco viewer,
// and the diff toggle. WP-011 lands the route stub so the URL shape
// resolves.

import { useParams } from "react-router-dom";

export function ThreadView() {
  const { changeId } = useParams<{ changeId: string }>();
  return (
    <section data-testid="page-thread">
      <h1>Thread {changeId ?? "(unknown)"}</h1>
      <p>Chat + files + diff land in WP-013/014/015.</p>
    </section>
  );
}
