import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import PracticePage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() =>
  vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }),
);
afterEach(() => vi.restoreAllMocks());

function renderPractice() {
  return render(
    <AuthProvider>
      <PracticePage />
    </AuthProvider>,
  );
}

describe("PracticePage", () => {
  it("lists themes and enables Commencer only once a theme is selected", async () => {
    vi.spyOn(api, "getPracticeThemes").mockResolvedValue([
      { theme: "panneaux", count: 3 },
      { theme: "vitesse", count: 2 },
    ]);
    renderPractice();
    expect(await screen.findByText("panneaux")).toBeInTheDocument();
    const commencer = screen.getByRole("button", { name: "Commencer" });
    expect(commencer).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /panneaux/ }));
    expect(commencer).toBeEnabled();
  });

  it("starts a session with the selected themes and shows the first question", async () => {
    vi.spyOn(api, "getPracticeThemes").mockResolvedValue([
      { theme: "panneaux", count: 1 },
    ]);
    const getQs = vi.spyOn(api, "getPracticeQuestions").mockResolvedValue([
      {
        id: 1, theme: "panneaux", text: "Question test ?", media_path: null,
        media_type: "none", explanation: "Expl",
        options: [
          { id: 1, label: "A", text: "A", is_correct: true },
          { id: 2, label: "B", text: "B", is_correct: false },
        ],
      },
    ]);
    renderPractice();
    await userEvent.click(await screen.findByRole("button", { name: /panneaux/ }));
    await userEvent.click(screen.getByRole("button", { name: "Commencer" }));
    await waitFor(() =>
      expect(screen.getByText("Question test ?")).toBeInTheDocument(),
    );
    expect(getQs).toHaveBeenCalledWith(["panneaux"]);
  });
});
