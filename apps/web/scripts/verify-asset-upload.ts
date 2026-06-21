import assert from "node:assert/strict";

import {
  ASSET_MAX_FILE_SIZE_BYTES,
  buildAssetObjectKey,
  getAssetFileValidationError,
  sanitizeAssetFileName,
} from "../lib/assets";

assert.equal(sanitizeAssetFileName("..\\..//evil 中文.png"), "evil-png");
assert.equal(sanitizeAssetFileName("my cute cat.webp"), "my-cute-cat.webp");
assert.equal(sanitizeAssetFileName("!!!"), "asset");
assert.equal(getAssetFileValidationError("image/png", ASSET_MAX_FILE_SIZE_BYTES), null);
assert.equal(getAssetFileValidationError("application/javascript", 10), "暂不支持该文件类型");
assert.equal(getAssetFileValidationError("image/png", ASSET_MAX_FILE_SIZE_BYTES + 1), "单文件不能超过 10MB");

const objectKey = buildAssetObjectKey({
  userId: "user_123",
  assetId: "asset_456",
  fileName: "..\\demo.png",
});

assert.equal(objectKey, "assets/user_123/asset_456/demo.png");

console.log("asset upload rules ok");
