import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScoreBanner } from "./ScoreBanner";

describe("ScoreBanner", () => {
  it("shows a passing state", () => {
    render(<ScoreBanner score={38} total={40} passed />);
    expect(screen.getByText("/ 40")).toBeInTheDocument();
    expect(screen.getByText(/Réussi/)).toBeInTheDocument();
  });

  it("shows a failing state", () => {
    render(<ScoreBanner score={20} total={40} passed={false} />);
    expect(screen.getByText(/Échoué/)).toBeInTheDocument();
  });
});
