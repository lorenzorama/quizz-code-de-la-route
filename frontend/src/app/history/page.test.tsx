import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import HistoryPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() => vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }));
afterEach(() => vi.restoreAllMocks());

function renderHistory() {
  return render(
    <AuthProvider>
      <HistoryPage />
    </AuthProvider>,
  );
}

describe("HistoryPage", () => {
  it("lists completed attempts with a pass badge and a review link", async () => {
    vi.spyOn(api, "getHistory").mockResolvedValue([
      { id: 9, started_at: "2026-07-04T10:00:00Z", finished_at: "2026-07-04T10:10:00Z", score: 38, passed: true, status: "completed" },
    ]);
    renderHistory();
    expect(await screen.findByText(/Score 38 \/ 40/)).toBeInTheDocument();
    expect(screen.getByText("Réussi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Revoir" })).toHaveAttribute(
      "href",
      "/exam/9/review",
    );
  });

  it("shows an empty state when there are no attempts", async () => {
    vi.spyOn(api, "getHistory").mockResolvedValue([]);
    renderHistory();
    expect(await screen.findByText(/Aucun examen/)).toBeInTheDocument();
  });
});
