// frontend/src/lib/sse.ts
/**
 * Zero-dependency Server-Sent Events (SSE) reader for React.
 * Supports HTTP POST, custom authorization headers, payload serialization,
 * line-by-line decoding, and instant client abort via AbortController.
 */

export interface SSEOptions {
  method?: "GET" | "POST";
  headers?: Record<string, string>;
  body?: any;
  signal?: AbortSignal;
}

export interface SSECallbacks {
  onEvent?: (event: string, data: any) => void;
  onStatus?: (data: { stage?: string; message: string; step?: number }) => void;
  onThought?: (step: any) => void;
  onToolStart?: (tool: any) => void;
  onToolEnd?: (tool: any) => void;
  onToken?: (delta: string) => void;
  onComplete?: (payload: any) => void;
  onError?: (error: Error) => void;
}

export async function fetchEventStream(
  url: string,
  options: SSEOptions,
  callbacks: SSECallbacks
): Promise<void> {
  const { method = "POST", headers = {}, body, signal } = options;

  let requestBody: any = undefined;
  const requestHeaders: Record<string, string> = {
    Accept: "text/event-stream",
    ...headers,
  };

  if (body) {
    if (body instanceof FormData) {
      requestBody = body;
    } else if (typeof body === "string") {
      requestBody = body;
      if (!requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "application/json";
      }
    } else {
      requestBody = JSON.stringify(body);
      if (!requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "application/json";
      }
    }
  }

  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: requestBody,
    signal,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    const err = new Error(errorDetail);
    callbacks.onError?.(err);
    throw err;
  }

  if (!response.body) {
    const err = new Error("Response body is empty.");
    callbacks.onError?.(err);
    throw err;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let currentEvent = "message";
  let currentDataLines: string[] = [];

  const dispatchEvent = () => {
    if (currentDataLines.length === 0) return;
    const rawData = currentDataLines.join("\n");
    let parsedData: any = rawData;
    try {
      parsedData = JSON.parse(rawData);
    } catch {
      // raw string data
    }

    callbacks.onEvent?.(currentEvent, parsedData);

    switch (currentEvent) {
      case "status":
        callbacks.onStatus?.(parsedData);
        break;
      case "thought":
        callbacks.onThought?.(parsedData);
        break;
      case "tool_start":
        callbacks.onToolStart?.(parsedData);
        break;
      case "tool_end":
        callbacks.onToolEnd?.(parsedData);
        break;
      case "token":
        callbacks.onToken?.(parsedData?.delta ?? rawData);
        break;
      case "complete":
        callbacks.onComplete?.(parsedData);
        break;
      case "error":
        callbacks.onError?.(new Error(parsedData?.message || rawData));
        break;
    }

    currentEvent = "message";
    currentDataLines = [];
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith(":")) {
          // SSE comment / heartbeat
          continue;
        } else if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          currentDataLines.push(line.slice(5).trimStart());
        } else if (line === "") {
          dispatchEvent();
        }
      }
    }

    // Flush any trailing buffer
    if (buffer.trim()) {
      if (buffer.startsWith("data:")) {
        currentDataLines.push(buffer.slice(5).trimStart());
      }
      dispatchEvent();
    }
  } catch (err: any) {
    if (err.name === "AbortError") {
      // Normal client cancellation
      return;
    }
    callbacks.onError?.(err);
    throw err;
  } finally {
    reader.releaseLock();
  }
}
