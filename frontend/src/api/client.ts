const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type TurnResponse = {
  conversation_id: string;
  transcript?: string;
  action: string;
  expression: string;
  animation: string;
  speech_text?: string;
  audio_base64?: string;
  audio_mime_type?: string;
  debug: Record<string, unknown>;
};

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
};

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = data?.error?.message ?? `HTTP ${response.status}`;
    throw new Error(message);
  }
  return data as T;
}

export function audioUrlFromBase64(base64: string, mime = "audio/mpeg") {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

