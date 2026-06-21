import { NextResponse } from "next/server";

import {
  buildAssetObjectKey,
  getAssetFileValidationError,
  sanitizeAssetFileName,
} from "@/lib/assets";
import { getCurrentUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { putObject } from "@/lib/storage";

export async function POST(request: Request) {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const formData = await request.formData().catch(() => null);
  const file = formData?.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "请上传文件" }, { status: 400 });
  }

  const validationError = getAssetFileValidationError(file.type, file.size);

  if (validationError) {
    return NextResponse.json({ error: validationError }, { status: 400 });
  }

  const assetId = crypto.randomUUID();
  const fileName = sanitizeAssetFileName(file.name);
  const objectKey = buildAssetObjectKey({
    userId: user.id,
    assetId,
    fileName,
  });
  const bytes = Buffer.from(await file.arrayBuffer());
  const uploaded = await putObject({
    key: objectKey,
    body: bytes,
    contentType: file.type,
  });

  const asset = await prisma.asset.create({
    data: {
      id: assetId,
      ownerId: user.id,
      fileName,
      mimeType: file.type,
      size: file.size,
      objectKey: uploaded.key,
      publicUrl: uploaded.publicUrl,
    },
    select: {
      id: true,
      fileName: true,
      mimeType: true,
      size: true,
      objectKey: true,
      publicUrl: true,
      createdAt: true,
    },
  });

  return NextResponse.json(
    {
      assetId: asset.id,
      objectKey: asset.objectKey,
      publicUrl: asset.publicUrl,
      asset,
    },
    { status: 201 },
  );
}
