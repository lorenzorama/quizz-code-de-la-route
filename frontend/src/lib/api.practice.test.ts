import { afterEach, describe, expect, it, vi } from "vitest";
import { getPracticeQuestions, getPracticeThemes } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("practice api", () => {
  it("getPracticeThemes GETs /practice/themes", async () => {
    const fetchMock = mockFetch(200, [{ theme: "panneaux", count: 3 }]);
    vi.stubGlobal("fetch", fetchMock);
    const res = await getPracticeThemes();
    expect(res).toEqual([{ theme: "panneaux", count: 3 }]);
    expect(fetchMock.mock.calls[0][0]).toContain("/practice/themes");
  });

  it("getPracticeQuestions builds repeated, encoded theme params", async () => {
    const fetchMock = mockFetch(200, []);
    vi.stubGlobal("fetch", fetchMock);
    await getPracticeQuestions(["panneaux", "priorités"]);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain(
      "/practice/questions?theme=panneaux&theme=priorit%C3%A9s",
    );
    expect(fetchMock.mock.calls[0][1].credentials).toBe("include");
  });
});
