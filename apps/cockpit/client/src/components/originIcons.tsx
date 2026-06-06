// WP-P10 — Heroicons (MIT, Tailwind Labs) used by the change-origin surfaces.
//
// Real SVGs (20 mini solid / 24 outline), centralised so the badge + panel +
// lens markup stays readable. All decorative — `aria-hidden` is applied by the
// SVG (callers pass nothing). Consumes `currentColor`, so colour comes from the
// CSS module's token rules (worded status is never colour-alone — the icon
// pairs with a word).
//
//   bolt               = Autonomous
//   chat-bubble        = Assisted
//   question-mark-circle = Origin unknown
//   user               = Turn Card avatar
//   arrow-right        = "Open conversation →" / trace jumps
//   check              = run "Completed"
//   info               = honesty banner
//   chevron-down       = progressive-disclosure caret
//   clock              = "inferred from timing" note

import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;

const mini = (props: P, ...paths: string[]) => (
  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" {...props}>
    {paths.map((d, i) => (
      <path key={i} fillRule="evenodd" clipRule="evenodd" d={d} />
    ))}
  </svg>
);

export const BoltIcon = (p: P) => (
  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" {...p}>
    <path d="M11.983 1.907a.75.75 0 0 0-1.292-.657l-8.5 9.5A.75.75 0 0 0 2.75 12h6.572l-1.305 6.093a.75.75 0 0 0 1.292.657l8.5-9.5A.75.75 0 0 0 17.25 8h-6.572l1.305-6.093Z" />
  </svg>
);
export const ChatBubbleIcon = (p: P) =>
  mini(
    p,
    "M10 2c-2.236 0-4.43.18-6.57.524C1.993 2.755 1 4.014 1 5.426v5.148c0 1.413.993 2.67 2.43 2.902.848.137 1.705.248 2.57.331v3.443a.75.75 0 0 0 1.28.53l3.58-3.579a.78.78 0 0 1 .527-.224 41.202 41.202 0 0 0 5.183-.5c1.437-.232 2.43-1.49 2.43-2.903V5.426c0-1.413-.993-2.67-2.43-2.902A41.289 41.289 0 0 0 10 2Z",
  );
export const QuestionMarkCircleIcon = (p: P) =>
  mini(
    p,
    "M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0ZM8.94 6.94a.75.75 0 1 1-1.061-1.061 3 3 0 1 1 2.871 5.026v.345a.75.75 0 0 1-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 1 0 8.94 6.94ZM10 15a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
  );
export const UserIcon = (p: P) => (
  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" {...p}>
    <path d="M10 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM3.465 14.493a1.23 1.23 0 0 0 .41 1.412A9.957 9.957 0 0 0 10 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 0 0-13.074.003Z" />
  </svg>
);
export const ArrowRightIcon = (p: P) =>
  mini(
    p,
    "M3 10a.75.75 0 0 1 .75-.75h10.638L10.23 5.29a.75.75 0 1 1 1.04-1.08l5.5 5.25a.75.75 0 0 1 0 1.08l-5.5 5.25a.75.75 0 1 1-1.04-1.08l4.158-3.96H3.75A.75.75 0 0 1 3 10Z",
  );
export const CheckIcon = (p: P) =>
  mini(
    p,
    "M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z",
  );
export const InfoIcon = (p: P) =>
  mini(
    p,
    "M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z",
  );
export const ChevronDownIcon = (p: P) =>
  mini(
    p,
    "M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z",
  );
export const ClockIcon = (p: P) =>
  mini(
    p,
    "M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm.75-13a.75.75 0 0 0-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 0 0 0-1.5h-3.25V5Z",
  );
