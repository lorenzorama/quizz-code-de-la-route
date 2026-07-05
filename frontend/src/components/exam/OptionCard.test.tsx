import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OptionCard } from "./OptionCard";

const option = { id: 1, label: "A", text: "Priorité à droite" };

describe("OptionCard", () => {
  it("shows label + text and toggles on click", async () => {
    const onToggle = vi.fn();
    render(<OptionCard option={option} selected={false} onToggle={onToggle} />);
    const btn = screen.getByRole("button", { name: /Priorité à droite/ });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("reflects the selected state via aria-pressed", () => {
    render(<OptionCard option={option} selected onToggle={() => {}} />);
    expect(screen.getByRole("button", { name: /Priorité à droite/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
