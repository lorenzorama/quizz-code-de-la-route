import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import LoginPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

afterEach(() => vi.restoreAllMocks());

function renderLogin() {
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  it("logs in and redirects home on success", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com" });
    renderLogin();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("shows an error message when login fails", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockRejectedValue(
      new api.ApiError(401, "Invalid email or password"),
    );
    renderLogin();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password",
    );
  });
});
