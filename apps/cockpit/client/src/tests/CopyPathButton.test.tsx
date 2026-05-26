// WP-014 — <CopyPathButton /> tests.
//
// One button that copies the file's absolute filesystem path to the
// clipboard and shows a transient "Copied" confirmation. If the
// Clipboard API is unavailable, the button still renders (manual-copy
// fallback) and does not throw.
//
// References: WP-014 Contract (<CopyPathButton> shape).

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CopyPathButton } from "../components/CopyPathButton";

const ABS = "/Users/founder/worktree/src/index.ts";

describe("<CopyPathButton />", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders a button labelled 'Copy path'", () => {
    render(<CopyPathButton absolutePath={ABS} />);
    expect(
      screen.getByRole("button", { name: /copy path/i }),
    ).toBeInTheDocument();
  });

  it("writes the absolute path to the clipboard on click", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<CopyPathButton absolutePath={ABS} />);
    fireEvent.click(screen.getByRole("button", { name: /copy path/i }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(ABS));
  });

  it("shows a transient 'Copied' confirmation after a successful copy", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<CopyPathButton absolutePath={ABS} />);
    fireEvent.click(screen.getByRole("button", { name: /copy path/i }));

    await waitFor(() =>
      expect(screen.getByText(/copied/i)).toBeInTheDocument(),
    );
  });

  it("does not throw when the Clipboard API is unavailable", () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });

    render(<CopyPathButton absolutePath={ABS} />);
    const button = screen.getByRole("button", { name: /copy path/i });
    // Clicking must not throw even with no clipboard API.
    expect(() => fireEvent.click(button)).not.toThrow();
  });
});
