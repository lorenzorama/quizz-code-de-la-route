import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import { AuthProvider, useAuth } from "./auth";

function Probe() {
  const { user, loading, login, logout } = useAuth();
  if (loading) return <p>loading</p>;
  return (
    <div>
      <p>user: {user ? user.email : "none"}</p>
      <button onClick={() => login("a@b.com", "password123")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

afterEach(() => vi.restoreAllMocks());

describe("AuthProvider", () => {
  it("hydrates from getMe on mount (unauthenticated)", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
  });

  it("login sets the user, logout clears it", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com" });
    vi.spyOn(api, "logout").mockResolvedValue();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "login" }));
    });
    await waitFor(() => expect(screen.getByText("user: a@b.com")).toBeInTheDocument());
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "logout" }));
    });
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
  });
});
