import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getMe, login } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("login posts credentials and returns the user", async () => {
    const fetchMock = mockFetch(200, { id: 1, email: "a@b.com" });
    vi.stubGlobal("fetch", fetchMock);
    const user = await login("a@b.com", "password123");
    expect(user).toEqual({ id: 1, email: "a@b.com" });
    const [, options] = fetchMock.mock.calls[0];
    expect(options.credentials).toBe("include");
    expect(options.method).toBe("POST");
  });

  it("login throws ApiError with status on 401", async () => {
    vi.stubGlobal("fetch", mockFetch(401, { detail: "Invalid email or password" }));
    await expect(login("a@b.com", "wrong")).rejects.toMatchObject({
      status: 401,
      message: "Invalid email or password",
    });
    await expect(login("a@b.com", "wrong")).rejects.toBeInstanceOf(ApiError);
  });

  it("getMe returns null on 401 instead of throwing", async () => {
    vi.stubGlobal("fetch", mockFetch(401, { detail: "Not authenticated" }));
    expect(await getMe()).toBeNull();
  });

  it("getMe returns the user on 200", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { id: 7, email: "c@d.com" }));
    expect(await getMe()).toEqual({ id: 7, email: "c@d.com" });
  });
});
