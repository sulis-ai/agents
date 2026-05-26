// WP-012 — <RelativeTime> — trivial wrapper around formatRelativeTime.
//
// Used by ChangeCard and (eventually) thread surfaces. The `title`
// attribute carries the full ISO timestamp so a hover shows the exact
// time without needing a tooltip library.

import { formatRelativeTime } from "../utils/relativeTime";

export interface RelativeTimeProps {
  iso: string;
}

export function RelativeTime({ iso }: RelativeTimeProps) {
  return <time dateTime={iso} title={iso}>{formatRelativeTime(iso)}</time>;
}
