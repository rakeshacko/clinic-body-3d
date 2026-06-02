/** Presenter command protocol shared by the wall screen, the /remote tablet, and the ws relay. */
export type PresenterCommand =
  | { type: "NEXT" }
  | { type: "PREV" }
  | { type: "OVERVIEW" }
  | { type: "SELECT_INDEX"; index: number }
  | { type: "SELECT_SYSTEM"; id: string }
  | { type: "LOAD_MEMBER"; memberId: string };

export interface PresenterChannel {
  send(cmd: PresenterCommand): void;
  subscribe(cb: (cmd: PresenterCommand) => void): () => void;
  close(): void;
}

const RELAY_URL = import.meta.env.VITE_RELAY_URL ?? "ws://localhost:8787";
const MODE = (import.meta.env.VITE_REMOTE ?? "").toLowerCase();

/** Same-machine cross-tab sync. No server required — the single-device default. */
function createBroadcastChannel(): PresenterChannel {
  const bc = new BroadcastChannel("acko-presenter");
  return {
    send: (cmd) => bc.postMessage(cmd),
    subscribe: (cb) => {
      const handler = (e: MessageEvent) => cb(e.data as PresenterCommand);
      bc.addEventListener("message", handler);
      return () => bc.removeEventListener("message", handler);
    },
    close: () => bc.close(),
  };
}

/** Separate physical tablet over the clinic LAN via /server/remote-relay.ts. */
function createWsChannel(): PresenterChannel {
  let ws: WebSocket | null = null;
  const listeners = new Set<(cmd: PresenterCommand) => void>();
  const queue: PresenterCommand[] = [];

  const connect = () => {
    ws = new WebSocket(RELAY_URL);
    ws.addEventListener("open", () => {
      while (queue.length) ws!.send(JSON.stringify(queue.shift()));
    });
    ws.addEventListener("message", (e) => {
      try {
        const cmd = JSON.parse(String(e.data)) as PresenterCommand;
        listeners.forEach((cb) => cb(cmd));
      } catch {
        /* ignore malformed frames */
      }
    });
    ws.addEventListener("close", () => setTimeout(connect, 1000));
    ws.addEventListener("error", () => ws?.close());
  };
  connect();

  return {
    send: (cmd) => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(cmd));
      else queue.push(cmd);
    },
    subscribe: (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    close: () => ws?.close(),
  };
}

export const presenterChannel: PresenterChannel =
  MODE === "ws" ? createWsChannel() : createBroadcastChannel();

export const remoteMode: "ws" | "local" = MODE === "ws" ? "ws" : "local";
