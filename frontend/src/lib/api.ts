export type User = { id: number; email: string };

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function register(email: string, password: string): Promise<User> {
  return request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<User> {
  return request<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export type ExamOption = { id: number; label: string; text: string };

export type ExamQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  options: ExamOption[];
};

export type StartExamResponse = {
  attempt_id: number;
  question_count: number;
  questions: ExamQuestion[];
};

export type SubmittedAnswer = {
  question_id: number;
  selected_option_ids: number[];
  time_taken?: number | null;
};

export type ExamResult = {
  attempt_id: number;
  score: number;
  total: number;
  passed: boolean;
};

export type ReviewOption = {
  id: number;
  label: string;
  text: string;
  is_correct: boolean;
};

export type ReviewQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  explanation: string;
  options: ReviewOption[];
  selected_option_ids: number[];
  is_correct: boolean;
};

export type Review = {
  attempt_id: number;
  score: number;
  total: number;
  passed: boolean;
  questions: ReviewQuestion[];
};

export type AttemptSummary = {
  id: number;
  started_at: string;
  finished_at: string | null;
  score: number | null;
  passed: boolean | null;
  status: string;
};

export function startExam(): Promise<StartExamResponse> {
  return request<StartExamResponse>("/exam/start", { method: "POST" });
}

export function submitExam(
  attemptId: number,
  answers: SubmittedAnswer[],
): Promise<ExamResult> {
  return request<ExamResult>(`/exam/${attemptId}/submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function getReview(attemptId: number): Promise<Review> {
  return request<Review>(`/exam/${attemptId}/review`);
}

export function getHistory(): Promise<AttemptSummary[]> {
  return request<AttemptSummary[]>("/exam/history");
}

export function mediaUrl(path: string): string {
  return `${BASE_URL}/media/${path}`;
}

export type ThemeCount = { theme: string; count: number };

export type PracticeOption = {
  id: number;
  label: string;
  text: string;
  is_correct: boolean;
};

export type PracticeQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  explanation: string;
  options: PracticeOption[];
};

export function getPracticeThemes(): Promise<ThemeCount[]> {
  return request<ThemeCount[]>("/practice/themes");
}

export function getPracticeQuestions(
  themes: string[],
): Promise<PracticeQuestion[]> {
  const query = themes
    .map((t) => `theme=${encodeURIComponent(t)}`)
    .join("&");
  return request<PracticeQuestion[]>(`/practice/questions?${query}`);
}
