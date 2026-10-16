import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScenarioForm } from "../src/features/scenarios/ScenarioForm";
import { ErrorNotice, Modal, Pagination } from "../src/components/ui";
import { ApiError } from "../src/api/client";
import type { ScenarioRequest } from "../src/api/contracts";

const scenario: ScenarioRequest = {
  supplier_id: "S-04",
  as_of: "2026-10-15",
  outage_start: "2026-10-16",
  outage_end_exclusive: "2026-10-24",
  include_mitigation: true,
};
describe("accessible components (isolated props)", () => {
  it("requires valid dates before submitting", () => {
    render(
      <ScenarioForm
        draft={{ ...scenario, outage_end_exclusive: "2026-10-16" }}
        onChange={vi.fn()}
        onRun={vi.fn()}
        onCancel={vi.fn()}
        pending={false}
        suppliers={[]}
        ready
      />,
    );
    expect(
      screen.getByText("The exclusive end must be later than the start."),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: /Run scenario/ })).toBeDisabled();
  });
  it("does not calculate while disconnected", () => {
    render(
      <ScenarioForm
        draft={scenario}
        onChange={vi.fn()}
        onRun={vi.fn()}
        onCancel={vi.fn()}
        pending={false}
        suppliers={[]}
        ready={false}
      />,
    );
    expect(screen.getByRole("button", { name: /Run scenario/ })).toBeDisabled();
  });
  it("submits inputs and displays no guessed outcome", async () => {
    const run = vi.fn();
    render(
      <ScenarioForm
        draft={scenario}
        onChange={vi.fn()}
        onRun={run}
        onCancel={vi.fn()}
        pending={false}
        suppliers={[]}
        ready
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Run scenario/ }));
    expect(run).toHaveBeenCalledOnce();
    expect(screen.queryByText("1364.00")).not.toBeInTheDocument();
  });
  it("cancels an in-flight calculation", async () => {
    const cancel = vi.fn();
    render(
      <ScenarioForm
        draft={scenario}
        onChange={vi.fn()}
        onRun={vi.fn()}
        onCancel={cancel}
        pending
        suppliers={[]}
        ready
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Cancel calculation" }),
    );
    expect(cancel).toHaveBeenCalledOnce();
  });
  it("pages evidence without unbounded rendering", async () => {
    const changed = vi.fn();
    render(
      <Pagination
        total={10}
        offset={0}
        size={3}
        onChange={changed}
        label="paths"
      />,
    );
    expect(
      screen.getByRole("button", { name: "Previous paths" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next paths" }));
    expect(changed).toHaveBeenCalledWith(3);
  });
  it("announces an error with a safe retry", async () => {
    const retry = vi.fn();
    render(
      <ErrorNotice
        error={new ApiError(503, "database_unavailable")}
        onRetry={retry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Previous simulation is not shown as current",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Retry request/ }),
    );
    expect(retry).toHaveBeenCalledOnce();
  });
  it("restores focus and clears body scroll lock when a dialog unmounts", () => {
    const button = document.createElement("button");
    document.body.append(button);
    button.focus();
    const { unmount } = render(
      <Modal title="Review" onClose={vi.fn()}>
        <p>Review the plan</p>
      </Modal>,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Review");
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.activeElement).toBe(button);
    expect(document.body.style.overflow).toBe("");
    button.remove();
  });
});
