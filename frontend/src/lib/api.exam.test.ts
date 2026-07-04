import { afterEach, describe, expect, it, vi } from "vitest";
import { getHistory, getReview, mediaUrl, startExam, submitExam } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("exam api", () => {
  it("startExam POSTs to /exam/start", async () => {
    const fetchMock = mockFetch(201, { attempt_id: 5, question_count: 0, questions: [] });
    vi.stubGlobal("fetch", fetchMock);
    const res = await startExam();
    expect(res.attempt_id).toBe(5);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/exam/start");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
  });

  it("submitExam POSTs answers to the attempt", async () => {
    const fetchMock = mockFetch(200, { attempt_id: 5, score: 2, total: 3, passed: false });
    vi.stubGlobal("fetch", fetchMock);
    const res = await submitExam(5, [{ question_id: 1, selected_option_ids: [10] }]);
    expect(res.score).toBe(2);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/exam/5/submit");
    expect(JSON.parse(options.body)).toEqual({
      answers: [{ question_id: 1, selected_option_ids: [10] }],
    });
  });

  it("getReview GETs the review", async () => {
    const fetchMock = mockFetch(200, {
      attempt_id: 5, score: 3, total: 3, passed: true, questions: [],
    });
    vi.stubGlobal("fetch", fetchMock);
    const res = await getReview(5);
    expect(res.passed).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/exam/5/review");
  });

  it("getHistory GETs the history list", async () => {
    const fetchMock = mockFetch(200, [{ id: 1, started_at: "x", finished_at: null, score: null, passed: null, status: "in_progress" }]);
    vi.stubGlobal("fetch", fetchMock);
    const res = await getHistory();
    expect(res).toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toContain("/exam/history");
  });

  it("mediaUrl builds an absolute media URL", () => {
    expect(mediaUrl("signs/q1.jpg")).toMatch(/\/media\/signs\/q1\.jpg$/);
  });
});
