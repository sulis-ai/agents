// WP-P06 — <ProvenanceView /> tests (signed `provenance-prototype.html`).
//
// The dashboard front door (four digest tiles + two door-buttons + a quiet
// browse link), opening into the run-log and coverage-map lenses with a way
// back, and a per-requirement focused trace in the coverage lens. Empty state
// when there's no provenance. The component is presentational — it takes a
// ProvenanceView prop + a lifted focus selection (the data-fetch lives in
// <ProvenanceSection>), exactly like the rest of the thread's container/
// presentational split. Worded status never colour-alone.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import type {
  BrainView as BrainViewModel,
  FocusedTrace,
  ProvenanceView as ProvenanceModel,
} from "../../../shared/api-types";
import {
  ProvenanceView,
  type FocusState,
} from "../components/ProvenanceView";

function model(overrides: Partial<ProvenanceModel> = {}): ProvenanceModel {
  return {
    changeId: "01XYZ",
    digest: {
      did: 2,
      covered: { verified: 1, total: 49 },
      decided: 4,
      flagged: {
        count: 1,
        topGap: "Test coverage is thin on the payments path",
        selfCritique:
          "My confidence is in the spec, not in proven behaviour on payments.",
      },
    },
    runLog: [
      {
        runId: "run-verify",
        workflow: "Verify pass",
        stepName: "verify",
        at: "2026-05-21T11:58:00Z",
        outcome: "completed",
        confidence: 0.88,
        finalVerdict: "Checked the work against the requirements.",
        steps: [
          {
            step: "Read the 49 requirements",
            outcome: "done",
            detail: "Loaded all 49 requirements for the verify pass.",
            gap: null,
            selfCritique: null,
          },
          {
            step: "Ran the test suite for the payments path",
            outcome: "skip",
            detail: "1 test result, outcome: skip.",
            gap: "The payments test needs a sandbox key that isn't set here.",
            selfCritique: "A skipped test is not a passing test.",
          },
        ],
      },
      {
        runId: "run-specify",
        workflow: "Specify pass",
        stepName: "specify",
        at: "2026-05-20T09:10:00Z",
        outcome: "completed",
        confidence: null,
        finalVerdict: null,
        steps: [
          {
            step: "Drafted 49 requirements from the brief",
            outcome: "done",
            detail: null,
            gap: null,
            selfCritique: null,
          },
        ],
      },
    ],
    coverage: [
      {
        axis: "why",
        items: [
          { id: "op1", title: "Agents should run unattended and overnight" },
        ],
      },
      {
        axis: "what",
        items: [
          {
            id: "req-capture",
            title: "A payment must capture only after the order is confirmed",
            verified: false,
          },
          {
            id: "req-declined",
            title: "A declined payment must show a clear retry path",
            verified: true,
          },
        ],
      },
      {
        axis: "how",
        items: [
          {
            id: "des1",
            title: "Checkout payment flow design",
            kind: "design",
          },
          { id: "dec1", title: "Use short-lived tokens", kind: "decision" },
        ],
      },
      {
        axis: "tested",
        items: [
          {
            id: "sc1",
            title: "Declined card shows the retry path",
            outcome: "pass",
            kind: "scenario",
          },
          {
            id: "tr1",
            title: "Declined card retry — verified",
            outcome: "pass",
            kind: "testresult",
          },
        ],
      },
    ],
    ...overrides,
  };
}

const noFocus: FocusState = {
  trace: undefined,
  isLoading: false,
  isError: false,
};

function renderView(
  opts: {
    view?: ProvenanceModel;
    brain?: BrainViewModel;
    focusId?: string | null;
    focus?: FocusState;
    onFocus?: (id: string | null) => void;
  } = {},
) {
  return render(
    <ProvenanceView
      view={opts.view ?? model()}
      focusId={opts.focusId ?? null}
      onFocus={opts.onFocus ?? (() => {})}
      focus={opts.focus ?? noFocus}
      brain={opts.brain}
    />,
  );
}

describe("<ProvenanceView /> — dashboard front door (WP-P06)", () => {
  it("lands on the dashboard with the four digest tiles", () => {
    renderView();
    expect(screen.getByTestId("provenance-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("tile-did")).toBeInTheDocument();
    expect(screen.getByTestId("tile-covered")).toBeInTheDocument();
    expect(screen.getByTestId("tile-decided")).toBeInTheDocument();
    expect(screen.getByTestId("tile-flagged")).toBeInTheDocument();
  });

  it("shows the covered tile's verified-of-total and the trust tile's gap", () => {
    renderView();
    expect(
      screen.getByText(/49 requirements written · 1 proven by a test/),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("tile-flagged")).getByText(
        /Test coverage is thin on the payments path/,
      ),
    ).toBeInTheDocument();
    // self-critique surfaced honestly
    expect(
      screen.getByText(/My confidence is in the spec/),
    ).toBeInTheDocument();
  });

  it("shows the overall confidence from the newest run that carries one", () => {
    expect(renderView().getByTestId("provenance-confidence").textContent).toMatch(
      /88% confident/,
    );
  });

  it("flagged tile is honest when nothing is flagged", () => {
    renderView({
      view: model({
        digest: {
          did: 1,
          covered: { verified: 0, total: 3 },
          decided: 0,
          flagged: { count: 0, topGap: null, selfCritique: null },
        },
      }),
    });
    expect(
      within(screen.getByTestId("tile-flagged")).getByText("Nothing flagged"),
    ).toBeInTheDocument();
  });

  it("hides the browse link when there is no brain to browse", () => {
    renderView();
    expect(screen.queryByTestId("link-browse")).not.toBeInTheDocument();
  });
});

describe("<ProvenanceView /> — run-log lens (WP-P06)", () => {
  it("opens the run log via the door and shows the runs as cards", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-runlog"));
    const cards = screen.getAllByTestId("run-card");
    expect(cards).toHaveLength(2);
    expect(screen.getByText("Verify pass")).toBeInTheDocument();
  });

  it("expands a run to its steps and shows a step's detail/gap/critique", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-runlog"));
    // newest run is open by default; click the gap step.
    const steps = screen.getAllByTestId("step-item");
    const gapStep = steps.find((s) =>
      /Ran the test suite/.test(s.textContent ?? ""),
    )!;
    fireEvent.click(gapStep);
    const detail = screen.getByTestId("step-detail");
    expect(within(detail).getByText(/sandbox key/)).toBeInTheDocument();
    expect(
      within(detail).getByText(/A skipped test is not a passing test/),
    ).toBeInTheDocument();
    // worded status on the gap step, not colour-alone
    expect(within(gapStep).getByText("flagged")).toBeInTheDocument();
  });

  it("returns to the dashboard from a lens", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-runlog"));
    expect(screen.queryByTestId("provenance-dashboard")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("provenance-back"));
    expect(screen.getByTestId("provenance-dashboard")).toBeInTheDocument();
  });
});

describe("<ProvenanceView /> — coverage-map lens (WP-P06)", () => {
  it("opens the coverage map with the four columns and counts", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-coverage"));
    expect(screen.getByLabelText("Why — opportunities")).toBeInTheDocument();
    expect(screen.getByLabelText("What — requirements")).toBeInTheDocument();
    expect(
      screen.getByLabelText("How — designs and decisions"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Tested — scenarios and results"),
    ).toBeInTheDocument();
    // worded coverage status on a requirement (scoped to the requirements list)
    const list = screen.getByTestId("req-list");
    expect(within(list).getByText("Tested")).toBeInTheDocument();
    expect(within(list).getAllByText("Awaiting test").length).toBeGreaterThan(0);
  });

  it("labels each TESTED item by its actual kind (scenario vs test result)", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-coverage"));
    const tested = screen.getByLabelText("Tested — scenarios and results");
    // The column mixes a scenario and a test result — each carries its real
    // label, not a hardcoded "scenario" for both.
    expect(within(tested).getByText("scenario")).toBeInTheDocument();
    expect(within(tested).getByText("test result")).toBeInTheDocument();
  });

  it("filters the requirements list", () => {
    renderView();
    fireEvent.click(screen.getByTestId("door-coverage"));
    const filter = screen.getByTestId("req-filter");
    fireEvent.change(filter, { target: { value: "declined" } });
    const list = screen.getByTestId("req-list");
    expect(within(list).getByText(/declined payment/)).toBeInTheDocument();
    expect(
      within(list).queryByText(/capture only after the order/),
    ).not.toBeInTheDocument();
  });

  it("requests a focused trace when a requirement is clicked", () => {
    const onFocus = vi.fn();
    renderView({ onFocus });
    fireEvent.click(screen.getByTestId("door-coverage"));
    fireEvent.click(
      within(screen.getByTestId("req-list")).getByText(
        /capture only after the order/,
      ),
    );
    expect(onFocus).toHaveBeenCalledWith("req-capture");
  });

  it("renders the labelled focused trace once the trace resolves", () => {
    const trace: FocusedTrace = {
      requirementId: "req-capture",
      why: [{ id: "op1", title: "The founder needs to trust the work" }],
      how: [{ id: "des1", title: "Checkout payment flow design", kind: "design" }],
      tested: [{ id: "sc1", title: "Capture only after confirmation", outcome: "skip" }],
    };
    renderView({
      focusId: "req-capture",
      focus: { trace, isLoading: false, isError: false },
    });
    fireEvent.click(screen.getByTestId("door-coverage"));
    const body = screen.getByTestId("focus-trace-body");
    expect(within(body).getByText(/trust the work/)).toBeInTheDocument();
    expect(within(body).getByText("Checkout payment flow design")).toBeInTheDocument();
    // labelled edges
    expect(within(body).getByText("derived from")).toBeInTheDocument();
    expect(within(body).getByText("satisfied by")).toBeInTheDocument();
    // honest worded test status
    expect(within(body).getByText(/not run yet/)).toBeInTheDocument();
  });

  it("shows a loading state while the focused trace is in flight", () => {
    renderView({
      focusId: "req-capture",
      focus: { trace: undefined, isLoading: true, isError: false },
    });
    fireEvent.click(screen.getByTestId("door-coverage"));
    expect(screen.getByTestId("focus-loading")).toBeInTheDocument();
  });
});

describe("<ProvenanceView /> — browse everything + empty state", () => {
  const brain: BrainViewModel = {
    changeId: "01XYZ",
    groups: [
      {
        kind: "requirement",
        items: [
          {
            id: "r1",
            kind: "requirement",
            title: "A payment must capture only after confirmation",
            detail: { id: "r1" },
          },
        ],
      },
    ],
  };

  it("shows the browse link and reaches the flat BrainView fallback", () => {
    renderView({ brain });
    fireEvent.click(screen.getByTestId("link-browse"));
    expect(screen.getByLabelText("Browse everything")).toBeInTheDocument();
    expect(
      screen.getByText(/A payment must capture only after confirmation/),
    ).toBeInTheDocument();
  });

  it("shows the empty state when there is no provenance", () => {
    renderView({
      view: model({
        digest: {
          did: 0,
          covered: { verified: 0, total: 0 },
          decided: 0,
          flagged: { count: 0, topGap: null, selfCritique: null },
        },
        runLog: [],
        coverage: [],
      }),
    });
    expect(screen.getByTestId("provenance-empty")).toBeInTheDocument();
    expect(screen.getByText(/No provenance yet/)).toBeInTheDocument();
  });

  it("has no axe violations on the dashboard", async () => {
    const { container } = renderView({ brain });
    expect(await axe(container)).toHaveNoViolations();
  });
});
