import { DEFAULT_GATEWAY_URL } from "./constants";
import type { ExtensionSettings } from "./types";

const STORAGE_KEYS = ["gatewayUrl", "captureMic"] as const;

const toHttpUrl = (webSocketUrl: string): string => webSocketUrl.replace(/^ws/, "http");

export const loadSettings = async (): Promise<ExtensionSettings> => {
  const stored = await chrome.storage.local.get([...STORAGE_KEYS]);
  const gatewayWebSocketUrl =
    typeof stored.gatewayUrl === "string" && stored.gatewayUrl ? stored.gatewayUrl : DEFAULT_GATEWAY_URL;
  const captureMicrophone = typeof stored.captureMic === "boolean" ? stored.captureMic : true;
  return {
    gatewayWebSocketUrl,
    gatewayHttpUrl: toHttpUrl(gatewayWebSocketUrl),
    captureMicrophone,
  };
};

export const persistSettings = async (
  current: ExtensionSettings,
  updates: { gatewayUrl?: string; captureMicrophone?: boolean },
): Promise<ExtensionSettings> => {
  const next: ExtensionSettings = { ...current };
  if (updates.gatewayUrl) {
    next.gatewayWebSocketUrl = updates.gatewayUrl;
    next.gatewayHttpUrl = toHttpUrl(updates.gatewayUrl);
  }
  if (typeof updates.captureMicrophone === "boolean") next.captureMicrophone = updates.captureMicrophone;
  await chrome.storage.local.set({
    ...(updates.gatewayUrl ? { gatewayUrl: updates.gatewayUrl } : {}),
    ...(typeof updates.captureMicrophone === "boolean" ? { captureMic: updates.captureMicrophone } : {}),
  });
  return next;
};
