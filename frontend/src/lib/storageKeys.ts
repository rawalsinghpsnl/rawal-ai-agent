/**
 * rawal-ai-agent storage keys.
 * SPDX-License-Identifier: MIT
 *
 * Canonical prefix is `rawal.`. Legacy `bhati.` keys from pre-rebrand
 * installs are read as fallback and migrated forward on first access,
 * so existing users keep their settings, pins, drafts and outbox.
 */

const CANONICAL_PREFIX = "rawal.";
const LEGACY_PREFIX = "bhati.";

export function canonicalKey(suffix: string): string {
  return `${CANONICAL_PREFIX}${suffix}`;
}

function legacyKey(suffix: string): string {
  return `${LEGACY_PREFIX}${suffix}`;
}

/** Migrate one key: copy legacy -> canonical when canonical is missing. */
export function migrateKey(
  suffix: string,
  storage: Storage = localStorage,
): void {
  try {
    const next = canonicalKey(suffix);
    const prev = legacyKey(suffix);
    if (storage.getItem(next) == null) {
      const old = storage.getItem(prev);
      if (old != null) storage.setItem(next, old);
    }
  } catch {
    /* storage unavailable (private mode) */
  }
}

/** Migrate a list of suffixes in both localStorage and sessionStorage. */
export function migrateLegacyKeys(suffixes: string[]): void {
  for (const suffix of suffixes) {
    migrateKey(suffix, localStorage);
    try {
      const next = canonicalKey(suffix);
      const prev = legacyKey(suffix);
      if (sessionStorage.getItem(next) == null) {
        const old = sessionStorage.getItem(prev);
        if (old != null) sessionStorage.setItem(next, old);
      }
    } catch {
      /* ignore */
    }
  }
  // Dynamic per-project / per-thread keys (bhati.project, bhati.thread.*, bhati.pins.*)
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith(LEGACY_PREFIX)) {
        const suffix = k.slice(LEGACY_PREFIX.length);
        if (localStorage.getItem(canonicalKey(suffix)) == null) {
          const v = localStorage.getItem(k);
          if (v != null) localStorage.setItem(canonicalKey(suffix), v);
        }
      }
    }
  } catch {
    /* ignore */
  }
}

export function getWithLegacyFallback(
  suffix: string,
  storage: Storage = localStorage,
): string | null {
  try {
    return storage.getItem(canonicalKey(suffix)) ?? storage.getItem(legacyKey(suffix));
  } catch {
    return null;
  }
}

export function setCanonical(suffix: string, value: string, storage: Storage = localStorage): void {
  try {
    storage.setItem(canonicalKey(suffix), value);
  } catch {
    /* ignore */
  }
}
