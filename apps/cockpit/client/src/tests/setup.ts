// WP-001 — vitest setup for client tests.
//
// Imports the jest-dom matchers so .toBeInTheDocument() etc. work, and
// configures cleanup so each test starts from a clean DOM.

import "@testing-library/jest-dom/vitest";
import { afterEach, expect } from "vitest";
import { cleanup } from "@testing-library/react";
// WP-003 — register the jest-axe matcher so `expect(...).toHaveNoViolations()`
// works in component tests (WPF-06 a11y gate).
import { toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

afterEach(() => {
  cleanup();
});
