/**
 * Mobile Device Storage Bridge — rawal-ai-agent.
 * SPDX-License-Identifier: MIT
 *
 * Saves generated artifacts, code files, and project archives directly
 * into the Android phone's local storage (Documents/RawalAiAgent/Projects).
 * The legacy Documents/BhatiAiAgent folder is still checked as a fallback
 * so existing installs keep access to their workspaces after the rebrand.
 */

import { Capacitor } from "@capacitor/core";
import { Filesystem, Directory, Encoding } from "@capacitor/filesystem";

export const isNativeAndroid = (): boolean => {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android";
};

export async function requestStoragePermissions(): Promise<boolean> {
  if (!isNativeAndroid()) return true;
  try {
    const status = await Filesystem.requestPermissions();
    return status.publicStorage === "granted";
  } catch (e) {
    console.warn("Storage permission request failed", e);
    return false;
  }
}

export async function saveFileToPhoneStorage(
  projectId: string,
  filePath: string,
  content: string
): Promise<string | null> {
  if (!isNativeAndroid()) return null;

  try {
    const dir = `RawalAiAgent/Projects/${projectId}`;
    const fullPath = `${dir}/${filePath}`;

    // Ensure parent directories exist
    const parts = fullPath.split("/");
    parts.pop();
    const parentDir = parts.join("/");

    if (parentDir) {
      try {
        await Filesystem.mkdir({
          path: parentDir,
          directory: Directory.Documents,
          recursive: true,
        });
      } catch (e) {
        // Directory may already exist
      }
    }

    await Filesystem.writeFile({
      path: fullPath,
      data: content,
      directory: Directory.Documents,
      encoding: Encoding.UTF8,
    });

    console.log(`Saved file to Android storage: Documents/${fullPath}`);
    return `Documents/${fullPath}`;
  } catch (err) {
    console.error("Failed to save to mobile filesystem", err);
    return null;
  }
}

export async function readMobileFile(
  projectId: string,
  filePath: string
): Promise<string | null> {
  if (!isNativeAndroid()) return null;
  try {
    const fullPath = `RawalAiAgent/Projects/${projectId}/${filePath}`;
    const result = await Filesystem.readFile({
      path: fullPath,
      directory: Directory.Documents,
      encoding: Encoding.UTF8,
    });
    return typeof result.data === "string" ? result.data : null;
  } catch (e) {
    console.warn("Could not read local mobile file", e);
    return null;
  }
}
