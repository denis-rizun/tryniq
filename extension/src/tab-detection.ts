import { LOCAL_DEV_HOSTS, MEET_HOST } from "./constants";
import type { TabKind } from "./types";

export const detectTabKind = (): TabKind => {
  const host = location.hostname;
  if (host === MEET_HOST) return "meet";
  if (LOCAL_DEV_HOSTS.includes(host as typeof LOCAL_DEV_HOSTS[number])) return "fake-meet";
  return "other";
};

export const isInjectableTab = (tabKind: TabKind): boolean =>
  tabKind === "meet" || tabKind === "fake-meet";
