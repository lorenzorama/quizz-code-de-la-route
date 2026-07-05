import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuitToHome } from "./QuitToHome";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

afterEach(() => push.mockClear());

describe("QuitToHome", () => {
  it("opens a confirmation and navigates home on confirm", async () => {
    render(<QuitToHome message="Votre examen sera perdu." />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Quitter" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Oui, quitter" }));
    expect(push).toHaveBeenCalledWith("/");
  });

  it("closes without navigating on cancel", async () => {
    render(<QuitToHome message="Votre examen sera perdu." />);
    await userEvent.click(screen.getByRole("button", { name: "Quitter" }));
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(push).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
