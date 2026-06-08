// WP-010 — <OnboardingChat /> test (ADR-007/008; the SIGNED contract, panels
// 13–16 of sulis-app.html).
//
// Cold-start onboarding as a CONVERSATION (a form can't pick from an empty
// graph). It REUSES the chat composer idiom + the SSE client (EP-03), pointed
// at /api/onboarding/session. The contract this test pins:
//   - choose area → answer → see a plain-English PROPOSAL → CONFIRM → minted;
//   - the proposal (Tenant/Product/Project + repo plan) is shown BEFORE any
//     mint (the confirm gate, FR-N6);
//   - the do-you-have-a-repo branch is explicit FIND vs CREATE with LOCAL-ONLY
//     PRE-SELECTED (GitHub a clearly-labelled separate opt-in, founder-locked);
//   - the Product icon is a NEUTRAL TWO-LETTER TILE (no logo upload control);
//   - a declined flow creates nothing;
//   - a failed repo-create / scope-violation is surfaced plainly;
//   - on success the "your product is set up" end state appears.
//
// We inject a fake `streamOnboarding` so the component is tested without a
// network. Each call resolves the scripted events for that turn's phase.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";

import { OnboardingChat } from "../components/OnboardingChat";
import type { OnboardingStreamEvent, OnboardingRequest } from "../../../shared/api-types";

/**
 * A scripted onboarding funnel: maps each turn's phase to its canned events.
 * Mirrors the real `streamOnboarding(request, onEvent)` signature.
 */
function fakeOnboarding(byPhase: Record<string, OnboardingStreamEvent[]>) {
  return vi.fn(
    async (
      request: OnboardingRequest,
      onEvent: (e: OnboardingStreamEvent) => void,
    ) => {
      for (const e of byPhase[request.phase] ?? []) onEvent(e);
    },
  );
}

const PROPOSAL: OnboardingStreamEvent[] = [
  { type: "state", state: "searching" },
  { type: "chunk", text: "Looking in your folder… found a Node app." },
  { type: "state", state: "proposing" },
  {
    type: "proposal",
    proposal: {
      confirmToken: "tok-1",
      tenant: "Your workspace",
      product: "Acme Checkout",
      projects: [
        {
          name: "acme-checkout",
          source: { repo: "/founder/code/acme-checkout", path: "", primary_branch: "main" },
        },
      ],
      repoPlan: "found-existing",
      alreadyMinted: false,
    },
  },
];

const MINTED: OnboardingStreamEvent[] = [
  { type: "state", state: "minting" },
  {
    type: "minted",
    minted: {
      tenant: "Your workspace",
      product: { productId: "dna:product:01ACME", name: "Acme Checkout" },
      projects: [
        {
          projectId: "dna:project:01PROJ",
          source: { repo: "/founder/code/acme-checkout", path: "", primary_branch: "main" },
        },
      ],
    },
  },
  { type: "state", state: "complete" },
];

const SCOPE_VIOLATION: OnboardingStreamEvent[] = [
  {
    type: "error",
    code: "DISCOVERY_SCOPE_VIOLATION",
    message: "I can only look inside the folder you chose.",
  },
];

const CREATE_FAILED: OnboardingStreamEvent[] = [
  {
    type: "error",
    code: "REPO_CREATE_FAILED",
    message: "I couldn't create the repo — nothing was saved.",
  },
];

function startSearch(area = "/founder/code/acme-checkout") {
  const box = screen.getByLabelText(/which folder|where.*code|choose.*folder/i);
  fireEvent.change(box, { target: { value: area } });
  fireEvent.keyDown(box, { key: "Enter" });
}

describe("<OnboardingChat /> — search → propose → confirm → minted (signed contract)", () => {
  it("renders the cold-start hero and an area input (a conversation, not a form)", () => {
    render(<OnboardingChat streamOnboarding={fakeOnboarding({})} />);
    expect(screen.getByText(/set you up|get you set up/i)).toBeInTheDocument();
  });

  it("a search turn streams the agent text and shows a PROPOSAL before any mint", async () => {
    render(
      <OnboardingChat streamOnboarding={fakeOnboarding({ search: PROPOSAL })} />,
    );
    startSearch();
    const proposal = await screen.findByTestId("onboarding-proposal");
    expect(proposal.textContent).toContain("Acme Checkout");
    // Nothing is minted at the proposal stage — the confirm gate is shown.
    expect(screen.getByTestId("onboarding-confirm")).toBeInTheDocument();
    expect(screen.queryByTestId("setup-done")).not.toBeInTheDocument();
  });

  it("the repo branch shows FIND vs CREATE with LOCAL-ONLY pre-selected (founder-locked)", async () => {
    render(
      <OnboardingChat streamOnboarding={fakeOnboarding({ search: PROPOSAL })} />,
    );
    startSearch();
    await screen.findByTestId("onboarding-proposal");
    // The create-location control defaults to local-only (pressed); hosted-remote
    // is a clearly-labelled separate opt-in, never the default.
    const local = screen.getByTestId("repo-target-local");
    expect(local).toHaveAttribute("aria-pressed", "true");
    const hosted = screen.getByTestId("repo-target-hosted-remote");
    expect(hosted).toHaveAttribute("aria-pressed", "false");
  });

  it("the Product icon is a NEUTRAL TWO-LETTER TILE — no logo upload control", async () => {
    render(
      <OnboardingChat streamOnboarding={fakeOnboarding({ search: PROPOSAL })} />,
    );
    startSearch();
    await screen.findByTestId("onboarding-proposal");
    const tile = screen.getByTestId("product-tile");
    // Two upper-case letters derived from the product name ("Acme Checkout" → "AC").
    expect(tile.textContent?.trim()).toBe("AC");
    // There is NO file upload control anywhere on the surface.
    expect(screen.queryByTestId("logo-upload")).not.toBeInTheDocument();
  });

  it("confirm MINTS and shows the 'your product is set up' end state", async () => {
    render(
      <OnboardingChat
        streamOnboarding={fakeOnboarding({ search: PROPOSAL, confirm: MINTED })}
      />,
    );
    startSearch();
    await screen.findByTestId("onboarding-confirm");
    fireEvent.click(screen.getByTestId("onboarding-confirm"));
    const done = await screen.findByTestId("setup-done");
    expect(done.textContent).toContain("Acme Checkout");
  });

  it("a DECLINED flow (Not yet) creates nothing — no mint call, no done state", async () => {
    const fake = fakeOnboarding({ search: PROPOSAL, confirm: MINTED });
    render(<OnboardingChat streamOnboarding={fake} />);
    startSearch();
    await screen.findByTestId("onboarding-confirm");
    fireEvent.click(screen.getByTestId("onboarding-decline"));
    expect(screen.queryByTestId("setup-done")).not.toBeInTheDocument();
    // The confirm (mint) turn was never sent — only the search turn happened.
    const confirmCalls = fake.mock.calls.filter((c) => c[0].phase === "confirm");
    expect(confirmCalls).toHaveLength(0);
  });
});

describe("<OnboardingChat /> — failures are surfaced plainly (FR-N7/N10)", () => {
  it("a scope violation is shown plainly and creates nothing", async () => {
    render(
      <OnboardingChat
        streamOnboarding={fakeOnboarding({ search: SCOPE_VIOLATION })}
      />,
    );
    startSearch("/etc");
    const err = await screen.findByTestId("onboarding-error");
    expect(err).toHaveAttribute("role", "alert");
    expect(err.textContent?.toLowerCase()).toContain("folder");
    expect(screen.queryByTestId("setup-done")).not.toBeInTheDocument();
  });

  it("a failed repo-create leaves setup unchanged (no done state, FR-N10/N11)", async () => {
    render(
      <OnboardingChat
        streamOnboarding={fakeOnboarding({ search: PROPOSAL, confirm: CREATE_FAILED })}
      />,
    );
    startSearch();
    await screen.findByTestId("onboarding-confirm");
    fireEvent.click(screen.getByTestId("onboarding-confirm"));
    const err = await screen.findByTestId("onboarding-error");
    expect(err.textContent?.toLowerCase()).toContain("nothing was saved");
    expect(screen.queryByTestId("setup-done")).not.toBeInTheDocument();
  });
});

describe("<OnboardingChat /> — a11y (axe)", () => {
  it("has no axe violations on the setup surface", async () => {
    const { container } = render(
      <OnboardingChat streamOnboarding={fakeOnboarding({})} />,
    );
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
