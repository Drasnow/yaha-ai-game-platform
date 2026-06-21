from dataclasses import dataclass

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings


@dataclass(frozen=True)
class UploadResult:
    manifest_url: str
    entry_url: str
    artifact_base_url: str


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _content_type(file_name: str) -> str:
    for suffix, value in CONTENT_TYPES.items():
        if file_name.endswith(suffix):
            return value
    return "application/octet-stream"


class ArtifactStorage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name=settings.minio_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def upload_game_files(self, task_id: str, files: dict[str, str]) -> UploadResult:
        prefix = f"games/generated/{task_id}/v1"
        self._ensure_bucket()
        for file_name, content in files.items():
            self.client.put_object(
                Bucket=self.settings.minio_bucket,
                Key=f"{prefix}/{file_name}",
                Body=content.encode("utf-8"),
                ContentType=_content_type(file_name),
            )
        base_url = self._public_url(prefix)
        return UploadResult(
            manifest_url=f"{base_url}manifest.json",
            entry_url=f"{base_url}index.html",
            artifact_base_url=base_url,
        )

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.minio_bucket)
        except (BotoCoreError, ClientError):
            self.client.create_bucket(Bucket=self.settings.minio_bucket)

    def _public_url(self, prefix: str) -> str:
        endpoint = self.settings.minio_public_endpoint.rstrip("/")
        bucket = self.settings.minio_bucket.strip("/")
        return f"{endpoint}/{bucket}/{prefix.strip('/')}/"
