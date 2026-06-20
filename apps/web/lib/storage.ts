import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const MINIO_REGION = "us-east-1";

type PutObjectInput = {
  key: string;
  body: Buffer | Uint8Array | string;
  contentType?: string;
};

type StorageConfig = {
  endpoint: string;
  accessKeyId: string;
  secretAccessKey: string;
  bucket: string;
};

function requiredEnv(name: string) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

function getStorageConfig(): StorageConfig {
  return {
    endpoint: requiredEnv("MINIO_ENDPOINT"),
    accessKeyId: requiredEnv("MINIO_ACCESS_KEY"),
    secretAccessKey: requiredEnv("MINIO_SECRET_KEY"),
    bucket: requiredEnv("MINIO_BUCKET"),
  };
}

const globalForStorage = globalThis as unknown as {
  s3Client?: S3Client;
};

export function getS3Client() {
  if (!globalForStorage.s3Client) {
    const config = getStorageConfig();

    globalForStorage.s3Client = new S3Client({
      region: MINIO_REGION,
      endpoint: config.endpoint,
      forcePathStyle: true,
      credentials: {
        accessKeyId: config.accessKeyId,
        secretAccessKey: config.secretAccessKey,
      },
    });
  }

  return globalForStorage.s3Client;
}

export function getStorageBucket() {
  return getStorageConfig().bucket;
}

export function getPublicUrl(key: string) {
  const config = getStorageConfig();
  const endpoint = config.endpoint.replace(/\/$/, "");
  const normalizedKey = key.replace(/^\/+/, "");

  return `${endpoint}/${config.bucket}/${normalizedKey}`;
}

export async function putObject({ key, body, contentType }: PutObjectInput) {
  const bucket = getStorageBucket();
  const normalizedKey = key.replace(/^\/+/, "");

  await getS3Client().send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: normalizedKey,
      Body: body,
      ContentType: contentType,
    }),
  );

  return {
    bucket,
    key: normalizedKey,
    publicUrl: getPublicUrl(normalizedKey),
  };
}
