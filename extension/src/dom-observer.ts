import {
  DOM_LOOKUP_POLL_MS,
  DOM_LOOKUP_TIMEOUT_MS,
  LOCAL_SPEAKER_LABEL,
  MEET_TILE_SELECTORS,
  SPEAKER_FALLBACK_PREFIX,
} from "./constants";
import type { DomObserverEvent, ParticipantInfo } from "./types";

let unnamedSpeakerCounter = 0;

const queryAllTiles = (): NodeListOf<HTMLElement> =>
  document.querySelectorAll<HTMLElement>(MEET_TILE_SELECTORS.tileRoot);

const findTileBySsrc = (ssrc: number): HTMLElement | null => {
  for (const tile of queryAllTiles()) {
    const ssrcHolder = tile.querySelector(`[${MEET_TILE_SELECTORS.ssrcAttribute}]`);
    const value = ssrcHolder?.getAttribute(MEET_TILE_SELECTORS.ssrcAttribute);
    if (value && Number(value) === ssrc) return tile;
  }
  return null;
};

const isTileLocal = (tile: HTMLElement): boolean =>
  tile.querySelector(MEET_TILE_SELECTORS.selfMarker) !== null;

const isTileActive = (tile: HTMLElement): boolean => {
  const node = tile.querySelector(MEET_TILE_SELECTORS.activeSpeakerNode);
  return node?.classList.contains(MEET_TILE_SELECTORS.activeSpeakerClass) ?? false;
};

const expandShortName = (tile: HTMLElement, shortName: string): string | null => {
  let bestMatch: string | null = null;
  for (const labeledElement of tile.querySelectorAll<HTMLElement>("[aria-label]")) {
    const label = labeledElement.getAttribute("aria-label") ?? "";
    const match = label.match(/^([A-Z][^:]{1,80}):\s/);
    const candidate = match?.[1]?.trim();
    if (!candidate) continue;
    if (!candidate.startsWith(shortName) || candidate.length <= shortName.length) continue;
    if (!bestMatch || candidate.length > bestMatch.length) bestMatch = candidate;
  }
  return bestMatch;
};

const resolveDisplayName = (tile: HTMLElement, isLocal: boolean): string => {
  const nameSpan = tile.querySelector(MEET_TILE_SELECTORS.nameContainer) as HTMLElement | null;
  const primaryName = (nameSpan?.textContent ?? "").trim();

  if (primaryName && !primaryName.includes(" ")) {
    const expanded = expandShortName(tile, primaryName);
    if (expanded) return expanded;
  }
  if (primaryName) return primaryName;

  unnamedSpeakerCounter += 1;
  return isLocal ? LOCAL_SPEAKER_LABEL : `${SPEAKER_FALLBACK_PREFIX}${unnamedSpeakerCounter}`;
};

const buildParticipantInfo = (tile: HTMLElement): ParticipantInfo => {
  const isLocal = isTileLocal(tile);
  return {
    participantId: tile.dataset.participantId ?? null,
    displayName: resolveDisplayName(tile, isLocal),
    isLocal,
    isActive: isTileActive(tile),
    tileElement: tile,
  };
};

const buildFallbackInfo = (): ParticipantInfo => {
  unnamedSpeakerCounter += 1;
  return {
    participantId: null,
    displayName: `${SPEAKER_FALLBACK_PREFIX}${unnamedSpeakerCounter}`,
    isLocal: false,
    isActive: false,
    tileElement: null,
  };
};

export class DomObserver {
  private mutationObserver: MutationObserver | null = null;
  private activeSpeakerObserver: MutationObserver | null = null;
  private knownSsrcs = new Set<number>();

  constructor(private readonly onEvent: (event: DomObserverEvent) => void) {}

  start = (): void => {
    this.mutationObserver = new MutationObserver(() => this.scanForNewTiles());
    this.mutationObserver.observe(document.body, {
      subtree: true,
      attributes: true,
      childList: true,
      attributeFilter: [MEET_TILE_SELECTORS.ssrcAttribute, MEET_TILE_SELECTORS.participantIdAttribute, "class", "aria-label"],
    });
    this.activeSpeakerObserver = this.createActiveSpeakerObserver();
    this.activeSpeakerObserver.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"] });
    this.scanForNewTiles();
  };

  stop = (): void => {
    this.mutationObserver?.disconnect();
    this.activeSpeakerObserver?.disconnect();
    this.mutationObserver = null;
    this.activeSpeakerObserver = null;
  };

  lookupBySsrc = async (ssrc: number, timeoutMs = DOM_LOOKUP_TIMEOUT_MS): Promise<ParticipantInfo> => {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
      const tile = findTileBySsrc(ssrc);
      if (tile) return buildParticipantInfo(tile);
      await new Promise((resolve) => setTimeout(resolve, DOM_LOOKUP_POLL_MS));
    }
    return buildFallbackInfo();
  };

  guessRemoteSpeakerTile = (): HTMLElement | null => {
    const remoteTiles = Array.from(queryAllTiles()).filter((tile) => !isTileLocal(tile));
    const namedTiles = remoteTiles.filter((tile) => {
      const span = tile.querySelector(MEET_TILE_SELECTORS.nameContainer) as HTMLElement | null;
      return (span?.textContent ?? "").trim().length > 0;
    });
    const activeTile = namedTiles.find(isTileActive);
    if (activeTile) return activeTile;
    if (namedTiles.length === 1) return namedTiles[0] ?? null;
    return null;
  };

  buildInfoForTile = (tile: HTMLElement): ParticipantInfo => buildParticipantInfo(tile);

  private scanForNewTiles = (): void => {
    queryAllTiles().forEach((tile) => {
      const ssrcHolder = tile.querySelector(`[${MEET_TILE_SELECTORS.ssrcAttribute}]`);
      const ssrcValue = ssrcHolder?.getAttribute(MEET_TILE_SELECTORS.ssrcAttribute);
      if (!ssrcValue) return;
      const ssrc = Number(ssrcValue);
      if (!Number.isFinite(ssrc) || ssrc === 0 || this.knownSsrcs.has(ssrc)) return;
      this.knownSsrcs.add(ssrc);
      this.onEvent({ kind: "name", ssrc, info: buildParticipantInfo(tile) });
    });
  };

  private createActiveSpeakerObserver = (): MutationObserver => {
    const previousActiveStates = new WeakMap<Element, boolean>();
    return new MutationObserver((records) => {
      for (const record of records) {
        if (record.type !== "attributes" || record.attributeName !== "class") continue;
        const target = record.target as HTMLElement;
        if (!target.matches?.(MEET_TILE_SELECTORS.activeSpeakerNode)) continue;
        const tile = target.closest(`[${MEET_TILE_SELECTORS.participantIdAttribute}]`) as HTMLElement | null;
        const participantId = tile?.dataset.participantId;
        if (!participantId) continue;
        const isActive = target.classList.contains(MEET_TILE_SELECTORS.activeSpeakerClass);
        if (isActive === (previousActiveStates.get(target) ?? false)) continue;
        previousActiveStates.set(target, isActive);
        this.onEvent({ kind: "active", participantId, active: isActive, t: performance.now() / 1000 });
      }
    });
  };
}
