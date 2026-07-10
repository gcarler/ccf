/**
 * BroadcastChannel helper for CMS builder→preview sync.
 * When the builder saves section changes, it posts a message.
 * The preview page listens and auto-refreshes.
 */

const CHANNEL_NAME = "ccf-cms-preview-sync";

export interface PreviewSyncMessage {
  type: "section-saved" | "section-created" | "section-deleted" | "section-reordered";
  siteKey: string;
  slug: string;
  sectionId?: string;
  timestamp: number;
}

let channel: BroadcastChannel | null = null;

function getChannel(): BroadcastChannel | null {
  if (typeof window === "undefined") return null;
  if (!channel) {
    try {
      channel = new BroadcastChannel(CHANNEL_NAME);
    } catch {
      return null;
    }
  }
  return channel;
}

export function notifyPreviewSync(msg: Omit<PreviewSyncMessage, "timestamp">) {
  const ch = getChannel();
  if (!ch) return;
  ch.postMessage({ ...msg, timestamp: Date.now() });
}

export function subscribePreviewSync(
  handler: (msg: PreviewSyncMessage) => void,
): () => void {
  const ch = getChannel();
  if (!ch) return () => {};

  const listener = (e: MessageEvent<PreviewSyncMessage>) => {
    handler(e.data);
  };
  ch.addEventListener("message", listener);

  return () => {
    ch.removeEventListener("message", listener);
  };
}
