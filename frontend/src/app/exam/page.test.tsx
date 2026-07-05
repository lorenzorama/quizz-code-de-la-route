import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import ExamPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

function makeQuestions(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    theme: "priorités",
    text: `Question ${i + 1}`,
    media_path: null,
    media_type: "none",
    options: [
      { id: i * 10 + 1, label: "A", text: "A" },
      { id: i * 10 + 2, label: "B", text: "B" },
    ],
  }));
}

beforeEach(() => {
  push.mockClear();
  vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" });
});
afterEach(() => vi.restoreAllMocks());

function renderExam() {
  return render(
    <AuthProvider>
      <ExamPage />
    </AuthProvider>,
  );
}

describe("ExamPage runner", () => {
  it("shows an error when the bank is empty (409)", async () => {
    vi.spyOn(api, "startExam").mockRejectedValue(new api.ApiError(409, "empty"));
    renderExam();
    expect(await screen.findByText(/Aucune question disponible/)).toBeInTheDocument();
  });

  it("runs through questions, submits selected answers, and navigates to review", async () => {
    const questions = makeQuestions(2);
    vi.spyOn(api, "startExam").mockResolvedValue({
      attempt_id: 42,
      question_count: 2,
      questions,
    });
    const submit = vi
      .spyOn(api, "submitExam")
      .mockResolvedValue({ attempt_id: 42, score: 2, total: 2, passed: true });

    renderExam();

    // Q1: select A, click Suivant
    await screen.findByText("Question 1");
    await userEvent.click(screen.getByRole("button", { name: /^A/ }));
    await userEvent.click(screen.getByRole("button", { name: "Suivant" }));

    // Q2: select B, click Terminer
    await screen.findByText("Question 2");
    await userEvent.click(screen.getByRole("button", { name: /^B/ }));
    await userEvent.click(screen.getByRole("button", { name: "Terminer" }));

    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    const [attemptId, answers] = submit.mock.calls[0];
    expect(attemptId).toBe(42);
    expect(answers[0].selected_option_ids).toEqual([1]); // Q1 option A id
    expect(answers[1].selected_option_ids).toEqual([12]); // Q2 option B id
    await waitFor(() => expect(push).toHaveBeenCalledWith("/exam/42/review"));
  });

  it("auto-advances when the timer expires", async () => {
    vi.useFakeTimers();
    const questions = makeQuestions(2);
    vi.spyOn(api, "startExam").mockResolvedValue({
      attempt_id: 7,
      question_count: 2,
      questions,
    });
    vi.spyOn(api, "submitExam").mockResolvedValue({
      attempt_id: 7, score: 0, total: 2, passed: false,
    });
    renderExam();
    // flush the getMe (AuthProvider) and startExam microtasks
    for (let i = 0; i < 10 && !screen.queryByText("Question 1"); i++) {
      await vi.advanceTimersByTimeAsync(0);
    }
    expect(screen.getByText("Question 1")).toBeInTheDocument();
    // 20s → auto-advance to Q2
    await vi.advanceTimersByTimeAsync(20000);
    for (let i = 0; i < 10 && !screen.queryByText("Question 2"); i++) {
      await vi.advanceTimersByTimeAsync(0);
    }
    expect(screen.getByText("Question 2")).toBeInTheDocument();
    vi.useRealTimers();
  });
});
