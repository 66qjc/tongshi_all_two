"""SeaweedFS / S3 兼容存储适配器"""
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.services.storage_service import StoredObject


class S3StorageAdapter:
    """基于 boto3 的 S3 存储适配器"""

    def __init__(self):
        # 构建 boto3 配置：始终开启重试策略，条件开启 path-style 寻址
        config_kwargs: dict = {
            "retries": {"max_attempts": 3, "mode": "standard"},
        }
        if settings.s3_force_path_style:
            # SeaweedFS / MinIO 等本地 S3 网关需要 path-style 访问格式
            config_kwargs["s3"] = {"addressing_style": "path"}

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(**config_kwargs),
        )
        self._bucket_public = settings.s3_bucket_public
        self._bucket_private = settings.s3_bucket_private

    def _resolve_bucket(self, bucket_name: str = "") -> str:
        return bucket_name or self._bucket_public

    def save_bytes(
        self,
        *,
        content: bytes,
        object_key: str,
        content_type: str = "",
        bucket_name: str = "",
    ) -> StoredObject:
        bucket = self._resolve_bucket(bucket_name)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self._client.put_object(Bucket=bucket, Key=object_key, Body=content, **extra_args)
        return StoredObject(
            storage_provider="s3",
            bucket_name=bucket,
            object_key=object_key,
            stored_name=object_key,
            content_type=content_type,
            size_bytes=len(content),
        )

    def open_stream(self, *, object_key: str, bucket_name: str = "") -> BinaryIO:
        bucket = self._resolve_bucket(bucket_name)
        try:
            resp = self._client.get_object(Bucket=bucket, Key=object_key)
            return resp["Body"]
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"S3 对象不存在: {bucket}/{object_key}") from e
            raise

    def exists(self, *, object_key: str, bucket_name: str = "") -> bool:
        bucket = self._resolve_bucket(bucket_name)
        try:
            self._client.head_object(Bucket=bucket, Key=object_key)
            return True
        except ClientError:
            return False

    def delete(self, *, object_key: str, bucket_name: str = "") -> None:
        bucket = self._resolve_bucket(bucket_name)
        self._client.delete_object(Bucket=bucket, Key=object_key)
