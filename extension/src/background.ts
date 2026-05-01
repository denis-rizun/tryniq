import type { RuntimeMessage } from "./types";

const POPUP_TO_CONTENT_KINDS = new Set([
  "popup.start",
  "popup.stop",
  "popup.set_settings",
  "popup.mute_stream",
  "popup.get_state",
]);

const getActiveTabId = async (): Promise<number | null> => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.id ?? null;
};

const relayToActiveTab = async (
  message: RuntimeMessage,
  sendResponse: (response: unknown) => void,
): Promise<void> => {
  const tabId = await getActiveTabId();
  if (tabId === null) {
    sendResponse({ ok: false, error: "no active tab" });
    return;
  }
  try {
    const response = await chrome.tabs.sendMessage(tabId, message);
    sendResponse(response);
  } catch (error) {
    sendResponse({ ok: false, error: String(error) });
  }
};

chrome.runtime.onMessage.addListener((message: RuntimeMessage, _sender, sendResponse) => {
  if (POPUP_TO_CONTENT_KINDS.has(message.kind)) {
    void relayToActiveTab(message, sendResponse);
    return true;
  }
  if (message.kind === "content.state_update") {
    chrome.runtime.sendMessage(message).catch(() => {});
  }
  return false;
});
