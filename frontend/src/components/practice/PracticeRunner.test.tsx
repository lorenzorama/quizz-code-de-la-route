import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PracticeRunner } from "./PracticeRunner";
import type { PracticeQuestion } from "@/lib/api";

const questions: PracticeQuestion[] = [
  {
    id: 1, theme: "panneaux", text: "Q1 ?", media_path: null, media_type: "none",
    explanation: "Explication 1",
    options: [
      { id: 1, label: "A", text: "Bonne", is_correct: true },
      { id: 2, label: "B", text: "Mauvaise", is_correct: false },
    ],
  },
  {
    id: 2, theme: "vitesse", text: "Q2 ?", media_path: null, media_type: "none",
    explanation: "Explication 2",
    options: [
      { id: 3, label: "A", text: "A", is_correct: false },
      { id: 4, label: "B", text: "B", is_correct: true },
    ],
  },
];

describe("PracticeRunner", () => {
  it("has no timer/countdown", () => {
    render(<PracticeRunner questions={questions} onFinish={() => {}} />);
    expect(screen.queryByText(/Temps restant/)).not.toBeInTheDocument();
  });

  it("reveals explanation + verdict after Vérifier, then advances on Suivant", async () => {
    render(<PracticeRunner questions={questions} onFinish={() => {}} />);
    expect(screen.getByText("Q1 ?")).toBeInTheDocument();
    const verify = screen.getByRole("button", { name: "Vérifier" });
    expect(verify).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /Bonne/ }));
    await userEvent.click(verify);
    expect(screen.getByText("Explication 1")).toBeInTheDocument();
    expect(screen.getByText("Correct")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Suivant" }));
    expect(screen.getByText("Q2 ?")).toBeInTheDocument();
  });

  it("shows Terminer on the last question and calls onFinish", async () => {
    const onFinish = vi.fn();
    render(<PracticeRunner questions={[questions[0]]} onFinish={onFinish} />);
    await userEvent.click(screen.getByRole("button", { name: /Bonne/ }));
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    await userEvent.click(screen.getByRole("button", { name: "Terminer" }));
    expect(onFinish).toHaveBeenCalledOnce();
  });
});
