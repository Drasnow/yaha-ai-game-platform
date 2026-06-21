export const ASSET_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

export const ALLOWED_ASSET_MIME_TYPES = [
  "image/png",
  "image/jpeg",
  "image/webp",
  "text/plain",
] as const;

const allowedMimeTypes = new Set<string>(ALLOWED_ASSET_MIME_TYPES);

export function sanitizeAssetFileName(fileName: string) {
  const baseName = fileName
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)
    .pop();

  const sanitized = (baseName ?? "asset")
    .normalize("NFKD")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/\.+/g, ".")
    .replace(/-\./g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/^\.+|\.+$/g, "");

  return sanitized || "asset";
}

export function getAssetFileValidationError(mimeType: string, size: number) {
  if (!allowedMimeTypes.has(mimeType)) {
    return "暂不支持该文件类型";
  }

  if (size <= 0) {
    return "文件不能为空";
  }

  if (size > ASSET_MAX_FILE_SIZE_BYTES) {
    return "单文件不能超过 10MB";
  }

  return null;
}

type BuildAssetObjectKeyInput = {
  userId: string;
  assetId: string;
  fileName: string;
};

export function buildAssetObjectKey({ userId, assetId, fileName }: BuildAssetObjectKeyInput) {
  return `assets/${userId}/${assetId}/${sanitizeAssetFileName(fileName)}`;
}
