export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  id?: string;
  source: string;
  page: number | null;
  snippet: string | null;
  score: number | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations?: Citation[];
}

export interface ApiError {
  detail: string | Array<{ msg: string; loc: unknown[]; type: string }>;
}
