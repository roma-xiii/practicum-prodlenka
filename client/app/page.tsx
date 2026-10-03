"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Status =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ok"; message: string }
  | { state: "error"; message: string };

export default function Home() {
  const [status, setStatus] = useState<Status>({ state: "idle" });

  async function checkServer() {
    setStatus({ state: "loading" });
    try {
      const response = await fetch(`${API_URL}/api/hello`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = (await response.json()) as { message: string };
      setStatus({ state: "ok", message: data.message });
    } catch (error) {
      setStatus({
        state: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">Practicum Prodlenka</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Next.js client &rarr; FastAPI server
      </p>
      <button
        type="button"
        onClick={checkServer}
        className="rounded-full bg-foreground px-5 py-2 font-medium text-background transition-colors hover:opacity-90"
      >
        Проверить сервер
      </button>
      {status.state === "loading" && <p>Загрузка…</p>}
      {status.state === "ok" && <p>Ответ: {status.message}</p>}
      {status.state === "error" && (
        <p className="text-red-600">Ошибка: {status.message}</p>
      )}
    </main>
  );
}
