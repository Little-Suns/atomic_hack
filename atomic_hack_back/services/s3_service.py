"""S3 service for file storage operations"""
import asyncio
import io
import os
from typing import Optional

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    from boto3.s3.transfer import TransferConfig
except ImportError:
    boto3 = None
    Config = None
    BotoCoreError = Exception
    ClientError = Exception
    TransferConfig = None


# Configuration
# Поддерживаем оба варианта переменных: AWS_* и S3_*
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME") or os.getenv("TEMPLATE_BUCKET_NAME")
S3_REGION = os.getenv("AWS_REGION") or os.getenv("S3_REGION", "ru-central1")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_ACCESS_KEY")
S3_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN") or os.getenv("S3_SESSION_TOKEN")
S3_ADDRESSING_STYLE = os.getenv("S3_ADDRESSING_STYLE", "auto")
S3_USE_SSL = os.getenv("S3_USE_SSL", "true").lower() != "false"

GB = 1024 ** 3
DEFAULT_TRANSFER_CONFIG = TransferConfig(multipart_threshold=5*GB) if TransferConfig else None


def get_s3_client():
    """Creates S3 client with configuration"""
    if boto3 is None:
        raise RuntimeError("boto3 is not installed. Install with: pip install boto3")
    
    if not S3_ACCESS_KEY_ID or not S3_SECRET_ACCESS_KEY:
        raise RuntimeError(
            "S3 credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env"
        )
    
    if not S3_BUCKET_NAME:
        raise RuntimeError(
            "S3 bucket name not configured. Please set AWS_S3_BUCKET_NAME in .env"
        )
    
    session = boto3.session.Session(
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        aws_session_token=S3_SESSION_TOKEN,
        region_name=S3_REGION,
    )
    
    config_kwargs = {
        "signature_version": "s3v4",
        "s3": {"payload_signing_enabled": False},
    }
    
    if S3_ADDRESSING_STYLE:
        config_kwargs["s3"]["addressing_style"] = S3_ADDRESSING_STYLE
    
    client_kwargs = {
        "endpoint_url": S3_ENDPOINT_URL,
        "use_ssl": S3_USE_SSL
    }
    
    if Config is not None:
        client_kwargs["config"] = Config(**config_kwargs)
    
    return session.client("s3", **client_kwargs)


async def ensure_bucket_exists(bucket: str) -> bool:
    """
    Проверяет существование bucket и создает его если нужно
    
    Args:
        bucket: Имя bucket
        
    Returns:
        True если bucket существует или был создан, False при ошибке
    """
    try:
        s3_client = get_s3_client()
        
        # Проверяем существование bucket
        try:
            await asyncio.to_thread(s3_client.head_bucket, Bucket=bucket)
            print(f"✅ S3 bucket '{bucket}' exists")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == '404' or error_code == 'NoSuchBucket':
                # Bucket не существует - создаем
                print(f"📦 Creating S3 bucket '{bucket}'...")
                
                try:
                    # Для Yandex Cloud и других S3-совместимых хранилищ
                    # используем CreateBucketConfiguration только для AWS regions != us-east-1
                    create_bucket_kwargs = {"Bucket": bucket}
                    
                    # Для AWS regions кроме us-east-1 нужна LocationConstraint
                    if S3_REGION and S3_REGION != "us-east-1" and not S3_ENDPOINT_URL:
                        create_bucket_kwargs["CreateBucketConfiguration"] = {
                            "LocationConstraint": S3_REGION
                        }
                    
                    await asyncio.to_thread(
                        s3_client.create_bucket,
                        **create_bucket_kwargs
                    )
                    
                    print(f"✅ S3 bucket '{bucket}' created successfully")
                    return True
                except ClientError as create_error:
                    error_code = create_error.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = create_error.response.get('Error', {}).get('Message', str(create_error))
                    print(f"❌ Failed to create bucket '{bucket}': {error_code} - {error_msg}")
                    return False
            else:
                # Другая ошибка при проверке bucket
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                print(f"❌ Error checking bucket '{bucket}': {error_code} - {error_msg}")
                return False
                
    except Exception as e:
        print(f"❌ Error ensuring bucket exists: {type(e).__name__}: {str(e)}")
        return False


async def upload_bytes_to_s3(
    content: bytes,
    key: str,
    content_type: str = "application/octet-stream",
    bucket: Optional[str] = None
) -> str:
    """
    Upload bytes to S3
    
    Args:
        content: File content as bytes
        key: S3 object key
        content_type: MIME type
        bucket: S3 bucket name (defaults to S3_BUCKET_NAME)
        
    Returns:
        S3 key
    """
    bucket = bucket or S3_BUCKET_NAME
    
    # Убеждаемся что bucket существует (создаем при необходимости)
    bucket_exists = await ensure_bucket_exists(bucket)
    if not bucket_exists:
        raise RuntimeError(f"Failed to ensure bucket '{bucket}' exists")
    
    try:
        s3_client = get_s3_client()
        
        await asyncio.to_thread(
            s3_client.upload_fileobj,
            io.BytesIO(content),
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
            Config=DEFAULT_TRANSFER_CONFIG
        )
        
        print(f"✅ Uploaded to S3: {key} ({len(content)} bytes)")
        return key
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"❌ S3 upload failed: {error_code} - {error_msg}")
        raise RuntimeError(f"Failed to upload to S3 bucket '{bucket}' key '{key}': {error_msg}") from e
    except Exception as e:
        print(f"❌ S3 upload error: {type(e).__name__}: {str(e)}")
        raise RuntimeError(f"Failed to upload to S3: {str(e)}") from e


async def download_from_s3(
    key: str,
    bucket: Optional[str] = None
) -> bytes:
    """
    Download file from S3
    
    Args:
        key: S3 object key
        bucket: S3 bucket name
        
    Returns:
        File content as bytes
    """
    bucket = bucket or S3_BUCKET_NAME
    
    try:
        s3_client = get_s3_client()
        
        buffer = io.BytesIO()
        await asyncio.to_thread(
            s3_client.download_fileobj,
            bucket,
            key,
            buffer
        )
        
        buffer.seek(0)
        data = buffer.read()
        print(f"✅ Downloaded from S3: {key} ({len(data)} bytes)")
        return data
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code == 'NoSuchKey':
            print(f"❌ S3 file not found: {key}")
            raise FileNotFoundError(f"File not found in S3: {key}") from e
        elif error_code == 'NoSuchBucket':
            print(f"❌ S3 bucket not found: {bucket}")
            raise RuntimeError(f"S3 bucket not found: {bucket}") from e
        else:
            print(f"❌ S3 download failed: {error_code} - {error_msg}")
            raise RuntimeError(f"Failed to download from S3 bucket '{bucket}' key '{key}': {error_msg}") from e
    except Exception as e:
        print(f"❌ S3 download error: {type(e).__name__}: {str(e)}")
        raise RuntimeError(f"Failed to download from S3: {str(e)}") from e


async def generate_presigned_url(
    key: str,
    bucket: Optional[str] = None,
    expiration: int = 3600
) -> str:
    """
    Generate presigned URL for downloading
    
    Args:
        key: S3 object key
        bucket: S3 bucket name
        expiration: URL expiration time in seconds
        
    Returns:
        Presigned URL
    """
    bucket = bucket or S3_BUCKET_NAME
    s3_client = get_s3_client()
    
    url = await asyncio.to_thread(
        s3_client.generate_presigned_url,
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expiration
    )
    
    return url


async def delete_from_s3(
    key: str,
    bucket: Optional[str] = None
) -> bool:
    """
    Delete file from S3
    
    Args:
        key: S3 object key
        bucket: S3 bucket name
        
    Returns:
        True if deleted successfully
    """
    bucket = bucket or S3_BUCKET_NAME
    
    try:
        s3_client = get_s3_client()
        
        await asyncio.to_thread(
            s3_client.delete_object,
            Bucket=bucket,
            Key=key
        )
        print(f"✅ Deleted from S3: {key}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"❌ S3 delete failed for '{key}': {error_code} - {error_msg}")
        return False
    except Exception as e:
        print(f"❌ S3 delete error for '{key}': {type(e).__name__}: {str(e)}")
        return False


async def delete_prefix_from_s3(
    prefix: str,
    bucket: Optional[str] = None
) -> int:
    """
    Delete all objects with given prefix from S3 (recursive deletion of directory)
    
    Args:
        prefix: S3 prefix (directory path)
        bucket: S3 bucket name
        
    Returns:
        Number of deleted objects
    """
    bucket = bucket or S3_BUCKET_NAME
    deleted_count = 0
    
    try:
        s3_client = get_s3_client()
        
        # List all objects with this prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        # Delete objects in batches
        for page in pages:
            if 'Contents' not in page:
                continue
            
            objects = page['Contents']
            if not objects:
                continue
            
            # Delete up to 1000 objects at a time
            delete_list = [{'Key': obj['Key']} for obj in objects]
             
            await asyncio.to_thread(
                s3_client.delete_objects,
                Bucket=bucket,
                Delete={'Objects': delete_list}
            )
            
            deleted_count += len(delete_list)
        
        if deleted_count > 0:
            print(f"✅ Deleted {deleted_count} objects from S3 with prefix: {prefix}")
        else:
            print(f"ℹ️ No objects found with prefix: {prefix}")
        
        return deleted_count
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"❌ S3 delete prefix failed for '{prefix}': {error_code} - {error_msg}")
        return deleted_count
    except Exception as e:
        print(f"❌ S3 delete prefix error for '{prefix}': {type(e).__name__}: {str(e)}")
        return deleted_count


async def check_file_exists(
    key: str,
    bucket: Optional[str] = None
) -> bool:
    """
    Check if file exists in S3
    
    Args:
        key: S3 object key
        bucket: S3 bucket name
        
    Returns:
        True if exists
    """
    bucket = bucket or S3_BUCKET_NAME
    
    try:
        s3_client = get_s3_client()
        
        await asyncio.to_thread(
            s3_client.head_object,
            Bucket=bucket,
            Key=key
        )
        return True
    except ClientError:
        return False
    except Exception:
        return False


def check_s3_configuration() -> dict:
    """
    Проверяет конфигурацию S3 и возвращает статус
    
    Returns:
        dict с информацией о конфигурации
    """
    config_status = {
        "configured": False,
        "bucket_name": S3_BUCKET_NAME,
        "region": S3_REGION,
        "endpoint": S3_ENDPOINT_URL,
        "has_credentials": bool(S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY),
        "boto3_installed": boto3 is not None,
        "errors": []
    }
    
    if not boto3:
        config_status["errors"].append("boto3 not installed")
        return config_status
    
    if not S3_ACCESS_KEY_ID or not S3_SECRET_ACCESS_KEY:
        config_status["errors"].append("S3 credentials not set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
        return config_status
    
    if not S3_BUCKET_NAME:
        config_status["errors"].append("S3 bucket name not set (AWS_S3_BUCKET_NAME)")
        return config_status
    
    config_status["configured"] = True
    return config_status


async def test_s3_connection() -> bool:
    """
    Тестирует подключение к S3
    
    Returns:
        True если подключение работает
    """
    try:
        s3_client = get_s3_client()
        bucket = S3_BUCKET_NAME
        
        # Пытаемся получить список объектов (максимум 1)
        await asyncio.to_thread(
            s3_client.list_objects_v2,
            Bucket=bucket,
            MaxKeys=1
        )
        
        print(f"✅ S3 connection test successful: bucket '{bucket}' is accessible")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        print(f"❌ S3 connection test failed: {error_code}")
        return False
    except Exception as e:
        print(f"❌ S3 connection test error: {type(e).__name__}: {str(e)}")
        return False


async def load_template_with_fallback(
    template_bucket_id: Optional[str] = None,
    bucket: Optional[str] = None
) -> Optional[bytes]:
    """
    Загружает PPTX template с автоматическим fallback на default template.
    
    Порядок попыток:
    1. Если template_bucket_id указан - загружает его из S3
    2. Если не указан или загрузка не удалась - пытается загрузить DEFAULT_TEMPLATE_S3_KEY
    3. Если и default template не загружен - возвращает None (презентация создастся без template)
    
    Args:
        template_bucket_id: S3 ключ пользовательского template
        bucket: S3 bucket name (defaults to S3_BUCKET_NAME)
        
    Returns:
        bytes: Содержимое PPTX template или None если не загружен
        
    Example:
        >>> template_bytes = await load_template_with_fallback(presentation.template_bucket_id)
        >>> if template_bytes:
        ...     prs = Presentation(io.BytesIO(template_bytes))
        ... else:
        ...     prs = Presentation()  # Создание без template
    """
    template_bytes = None
    
    # Попытка 1: Загрузить пользовательский template
    if template_bucket_id:
        try:
            print(f"📥 Loading custom template from S3: {template_bucket_id}")
            template_bytes = await download_from_s3(template_bucket_id, bucket)
            print(f"✅ Custom template loaded ({len(template_bytes)} bytes)")
            return template_bytes
        except FileNotFoundError:
            print(f"⚠️ Custom template not found in S3: {template_bucket_id}")
        except Exception as e:
            print(f"⚠️ Could not load custom template: {type(e).__name__}: {e}")
    
    # Попытка 2: Загрузить default template
    default_template_key = os.getenv("DEFAULT_TEMPLATE_S3_KEY")
    if default_template_key:
        try:
            print(f"📥 Loading default template from S3: {default_template_key}")
            template_bytes = await download_from_s3(default_template_key, bucket)
            print(f"✅ Default template loaded ({len(template_bytes)} bytes)")
            return template_bytes
        except FileNotFoundError:
            print(f"⚠️ Default template not found in S3: {default_template_key}")
            print(f"💡 Hint: Upload default template to S3 at key: {default_template_key}")
        except Exception as e:
            print(f"⚠️ Could not load default template: {type(e).__name__}: {e}")
    else:
        print(f"ℹ️ DEFAULT_TEMPLATE_S3_KEY not configured in .env")
    
    # Возвращаем None если ничего не загружено
    print(f"💡 Will generate PPTX without template (using python-pptx defaults)")
    return None
