// WP-001 — vitest setup for client tests.
//
// Imports the jest-dom matchers so .toBeInTheDocument() etc. work, and
// configures cleanup so each test starts from a clean DOM.

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
