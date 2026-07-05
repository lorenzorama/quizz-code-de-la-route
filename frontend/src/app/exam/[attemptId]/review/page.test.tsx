import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import ReviewPage from "./page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ attemptId: "42" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() => vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }));
afterEach(() => vi.restoreAllMocks());

describe("ReviewPage", () => {
  it("shows the score and per-question corrections with explanations", async () => {
    vi.spyOn(api, "getReview").mockResolvedValue({
      attempt_id: 42,
      score: 1,
      total: 1,
      passed: false,
      questions: [
        {
          id: 1,
          theme: "priorités",
          text: "Qui passe ?",
          media_path: null,
          media_type: "none",
          explanation: "Priorité à droite.",
          selected_option_ids: [2],
          is_correct: false,
          options: [
            { id: 1, label: "A", text: "Moi", is_correct: true },
            { id: 2, label: "B", text: "L'autre", is_correct: false },
          ],
        },
      ],
    });
    render(
      <AuthProvider>
        <ReviewPage />
      </AuthProvider>,
    );
    expect(await screen.findByText("Qui passe ?")).toBeInTheDocument();
    expect(screen.getByText(/Priorité à droite/)).toBeInTheDocument();
    expect(screen.getByText("/ 1")).toBeInTheDocument();
    expect(screen.getByText("Incorrect")).toBeInTheDocument();
  });
});
