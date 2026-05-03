import io
import os
import uuid
import logging

try:
    import boto3  # type: ignore[import]
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.presentation import Presentation
from services.s3_service import check_s3_configuration, test_s3_connection, upload_bytes_to_s3

logger = logging.getLogger("app.files")

router = APIRouter()


def sanitize_filename(filename: str) -> str:
    """
    Build a safe filename by removing problematic characters.
    """
    import re

    safe_name = filename.replace(' ', '_')
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name)
    safe_name = safe_name.strip('_')
    if not safe_name:
        safe_name = 'presentation'
    return safe_name
_S3_BUCKET_NAME = os.getenv("TEMPLATE_BUCKET_NAME")
_S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
_S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
_S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")

os.environ.setdefault("AWS_CHUNKED_ENCODING_DISABLED", "true")


def _ensure_storage_configuration() -> None:
    if boto3 is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="boto3 library is not available in the backend environment",
        )
    missing_vars = []
    if not _S3_BUCKET_NAME:
        missing_vars.append("TEMPLATE_BUCKET_NAME")
    if not _S3_ENDPOINT_URL:
        missing_vars.append("S3_ENDPOINT_URL")
    if not _S3_ACCESS_KEY_ID:
        missing_vars.append("S3_ACCESS_KEY_ID")
    if not _S3_SECRET_ACCESS_KEY:
        missing_vars.append("S3_SECRET_ACCESS_KEY")
    if missing_vars:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage configuration missing environment variables: {', '.join(missing_vars)}",
        )
def _validate_pptx(file: UploadFile) -> None:
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pptx files are supported")
    allowed_types = {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type for PPTX")


@router.get("/checkDefaultTemplate")
async def check_default_template():
    """
    Проверяет наличие и доступность default template в S3
    
    Returns:
        dict: Статус конфигурации default template
    """
    from services.s3_service import check_file_exists
    
    default_template_key = os.getenv("DEFAULT_TEMPLATE_S3_KEY")
    
    result = {
        "configured": bool(default_template_key),
        "template_key": default_template_key,
        "exists": False,
        "accessible": False,
        "message": ""
    }
    
    if not default_template_key:
        result["message"] = "DEFAULT_TEMPLATE_S3_KEY not configured in .env"
        return result
    
    # Проверяем S3 конфигурацию
    try:
        _ensure_storage_configuration()
    except HTTPException as e:
        result["message"] = f"S3 not configured: {e.detail}"
        return result
    
    # Проверяем существование файла
    try:
        exists = await check_file_exists(default_template_key)
        result["exists"] = exists
        result["accessible"] = exists
        
        if exists:
            result["message"] = f"✅ Default template available at: {default_template_key}"
        else:
            result["message"] = f"⚠️ Default template not found in S3. Upload PPTX file to S3 key: {default_template_key}"
    except Exception as e:
        result["message"] = f"❌ Error checking default template: {str(e)}"
    
    return result


@router.post("/uploadTemplate")
async def upload_template(
    presentation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Загружает PPTX шаблон для презентации и сохраняет его в S3
    """
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    _validate_pptx(file)
    _ensure_storage_configuration()

    contents = await file.read()
    
    # Сохраняем PPTX шаблон в S3
    template_key = f"presentations/{presentation_id}/templates/{uuid.uuid4()}_{file.filename}"
    try:
        await upload_bytes_to_s3(
            content=contents,
            key=template_key,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        presentation.template_bucket_id = template_key
        logger.info(f"Template uploaded to S3: {template_key}")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload template to S3: {exc}",
        )

    # Сохраняем изменения в БД
    db.commit()
    db.refresh(presentation)

    return {
        "presentation_id": presentation.id,
        "template_bucket_id": presentation.template_bucket_id,
        "filename": file.filename,
        "message": "Template uploaded successfully."
    }

@router.post("/uploadContextFile")
async def upload_context_file(
    presentation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Загружает контекстный файл (PDF/DOCX/TXT/XLSX/PPTX) и создает RAG коллекцию
    """
    import tempfile
    from pathlib import Path
    from services.rag_service import create_rag_collection
    
    # Проверяем наличие необходимых API ключей
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured: OPENAI_API_KEY is missing in .env file"
        )
    
    # Проверяем существование презентации
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    
    # Валидация файла
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Проверяем размер (макс 50 MB)
    max_size = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 50MB"
        )
    
    # Сохраняем временно для обработки
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name
    
    try:
        # Создаем или добавляем в RAG коллекцию
        rag_id = await create_rag_collection(
            presentation_id=presentation_id,
            file_path=tmp_path,
            file_type=file_ext.lstrip('.'),
            existing_rag_id=presentation.rag_id
        )
        
        # Не загружаем контекстные файлы в S3 (только RAG коллекция)
        s3_key = None
        
        # Обновляем презентацию
        presentation.rag_id = rag_id
        
        # Добавляем файл в context_files JSON
        import json
        from datetime import datetime
        
        context_files = []
        if presentation.context_files:
            try:
                context_files = json.loads(presentation.context_files)
            except json.JSONDecodeError:
                context_files = []
        
        context_files.append({
            "filename": file.filename,
            "s3_key": s3_key,
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_type": file_ext.lstrip('.')
        })
        
        presentation.context_files = json.dumps(context_files, ensure_ascii=False)
        
        db.commit()
        db.refresh(presentation)
        
        return {
            "presentation_id": presentation_id,
            "rag_id": rag_id,
            "s3_key": s3_key,
            "filename": file.filename,
            "message": "Context file uploaded and processed successfully" + 
                      ("" if s3_key else " (S3 storage not configured - file not backed up)")
        }
    
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process context file: {exc}"
        ) from exc
    finally:
        # Удаляем временный файл
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


@router.get("/checkS3Status")
async def check_s3_status():
    """
    Проверяет конфигурацию и доступность S3
    """
    config_info = check_s3_configuration()
    
    if not config_info["configured"]:
        return {
            "status": "not_configured",
            "message": "S3 is not properly configured",
            "config": config_info,
            "connection_test": False
        }
    
    # Тестируем подключение
    connection_ok = await test_s3_connection()
    
    return {
        "status": "ok" if connection_ok else "connection_failed",
        "message": "S3 is configured and accessible" if connection_ok else "S3 configured but connection failed",
        "config": config_info,
        "connection_test": connection_ok
    }


@router.get("/downloadPptx")
async def download_pptx(
    presentation_id: int,
    db: Session = Depends(get_db)
):
    """
    Скачивает PPTX презентацию. Автоматически генерирует если отсутствует.
    """
    from fastapi.responses import StreamingResponse
    from services.pptx_generator import generate_pptx_from_slides
    from services.s3_service import download_from_s3, check_file_exists, upload_bytes_to_s3
    from sqlalchemy.orm import selectinload
    import json
    
    # Загружаем презентацию
    presentation = (
        db.query(Presentation)
        .options(selectinload(Presentation.slides))
        .filter(Presentation.id == presentation_id)
        .first()
    )
    
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    
    # Проверяем наличие контента слайдов
    slides_with_content = [s for s in presentation.slides if s.content_json]
    if not slides_with_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No slide content found. Please generate presentation content first"
        )
    
    # Пытаемся получить из S3 если настроен
    safe_filename = sanitize_filename(presentation.title)
    result_key = f"presentations/{presentation_id}/result/{safe_filename}.pptx"
    
    try:
        # Проверяем S3
        _ensure_storage_configuration()
        
        # Проверяем существование файла в S3
        if await check_file_exists(result_key):
            print(f"✅ PPTX found in S3, downloading and returning")
            pptx_bytes = await download_from_s3(result_key)
            
            from urllib.parse import quote
            filename = f"{safe_filename}.pptx"
            encoded_filename = quote(filename.encode('utf-8'))
            
            pptx_stream = io.BytesIO(pptx_bytes)
            pptx_stream.seek(0)
            
            print(f"📤 Sending cached PPTX: {len(pptx_bytes)} bytes, filename: {filename}")
            
            return StreamingResponse(
                pptx_stream,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                    "Content-Length": str(len(pptx_bytes))
                }
            )
    except Exception:
        pass
    
    # Генерируем PPTX on-the-fly
    print(f"🔧 Generating PPTX for presentation {presentation_id}")
    
    # Подготавливаем данные слайдов
    slides_data = []
    for slide in sorted(presentation.slides, key=lambda s: s.position):
        if slide.content_json:
            slides_data.append({
                "title": slide.title,
                "description": slide.description,
                "content_json": slide.content_json,
                "position": slide.position
            })
    
    # Загружаем template PPTX из S3 (с fallback на default template)
    from services.s3_service import load_template_with_fallback
    
    try:
        template_pptx_bytes = await load_template_with_fallback(
            template_bucket_id=presentation.template_bucket_id
        )
    except Exception as e:
        print(f"⚠️ Template loading error: {e}")
        template_pptx_bytes = None
    
    try:
        
        # Генерируем PPTX
        print(f"🔨 Generating PPTX with {len(slides_data)} slides...")
        pptx_bytes = await generate_pptx_from_slides(
            slides_data=slides_data,
            template_pptx_bytes=template_pptx_bytes,
            presentation_title=presentation.title
        )
        print(f"✅ PPTX generated successfully ({len(pptx_bytes)} bytes)")
        
        # Сохраняем в S3 для будущих запросов
        try:
            await upload_bytes_to_s3(
                content=pptx_bytes,
                key=result_key,
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            print(f"✅ PPTX saved to S3: {result_key}")
        except Exception as e:
            print(f"⚠️ Could not save to S3: {e}")
        
        # Возвращаем как StreamingResponse
        from urllib.parse import quote
        filename = f"{safe_filename}.pptx"
        # Кодируем filename для поддержки кириллицы (RFC 5987)
        encoded_filename = quote(filename.encode('utf-8'))
        
        # Создаем BytesIO и устанавливаем позицию в начало
        pptx_stream = io.BytesIO(pptx_bytes)
        pptx_stream.seek(0)
        
        print(f"📤 Sending PPTX: {len(pptx_bytes)} bytes, filename: {filename}")
        
        return StreamingResponse(
            pptx_stream,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Length": str(len(pptx_bytes))
            }
        )
        
    except Exception as exc:
        import traceback
        print(f"❌ Error generating PPTX: {type(exc).__name__}: {str(exc)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PPTX: {str(exc)}"
        ) from exc


@router.get("/downloadPdf")
async def download_pdf(
    presentation_id: int,
    db: Session = Depends(get_db)
):
    """
    Конвертирует PPTX презентацию в PDF и возвращает для скачивания
    Использует Gotenberg API для конвертации
    """
    from fastapi.responses import StreamingResponse
    from services.pptx_generator import generate_pptx_from_slides
    from services.pdf_converter import convert_pptx_to_pdf, check_gotenberg_health
    from services.s3_service import download_from_s3, check_file_exists, upload_bytes_to_s3
    from sqlalchemy.orm import selectinload
    import json
    
    # Проверяем доступность Gotenberg
    if not await check_gotenberg_health():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF conversion service (Gotenberg) is not available. Please check GOTENBERG_URL in .env"
        )
    
    # Загружаем презентацию
    presentation = (
        db.query(Presentation)
        .options(selectinload(Presentation.slides))
        .filter(Presentation.id == presentation_id)
        .first()
    )
    
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    
    # Проверяем наличие контента слайдов
    slides_with_content = [s for s in presentation.slides if s.content_json]
    if not slides_with_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No slide content found. Please generate presentation content first"
        )
    
    # Проверяем кеш PDF в S3
    safe_filename = sanitize_filename(presentation.title)
    pdf_result_key = f"presentations/{presentation_id}/result/{safe_filename}.pdf"
    pptx_result_key = f"presentations/{presentation_id}/result/{safe_filename}.pptx"
    
    try:
        _ensure_storage_configuration()
        
        # Проверяем существование PDF в S3
        if await check_file_exists(pdf_result_key):
            print(f"✅ PDF found in S3, returning cached version")
            pdf_bytes = await download_from_s3(pdf_result_key)
            
            from urllib.parse import quote
            filename = f"{safe_filename}.pdf"
            encoded_filename = quote(filename.encode('utf-8'))
            
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_stream.seek(0)
            
            print(f"📤 Sending PDF: {len(pdf_bytes)} bytes, filename: {filename}")
            
            return StreamingResponse(
                pdf_stream,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                    "Content-Length": str(len(pdf_bytes))
                }
            )
    except Exception as e:
        print(f"⚠️ S3 check failed: {e}")
    
    print(f"🔧 Generating PDF for presentation {presentation_id}")
    
    # Генерируем или загружаем PPTX
    pptx_bytes = None
    try:
        # Пытаемся загрузить готовый PPTX из S3
        if await check_file_exists(pptx_result_key):
            print(f"📥 Loading existing PPTX from S3")
            pptx_bytes = await download_from_s3(pptx_result_key)
    except Exception:
        pass
    
    if not pptx_bytes:
        # Генерируем PPTX
        print(f"🔧 Generating PPTX first...")
        slides_data = []
        for slide in sorted(presentation.slides, key=lambda s: s.position):
            if slide.content_json:
                slides_data.append({
                    "title": slide.title,
                    "description": slide.description,
                    "content_json": slide.content_json,
                    "position": slide.position
                })
        
        # Загружаем template (с fallback на default template)
        from services.s3_service import load_template_with_fallback
        
        try:
            template_pptx_bytes = await load_template_with_fallback(
                template_bucket_id=presentation.template_bucket_id
            )
        except Exception as e:
            print(f"⚠️ Template loading error: {e}")
            template_pptx_bytes = None
        
        pptx_bytes = await generate_pptx_from_slides(
            slides_data=slides_data,
            template_pptx_bytes=template_pptx_bytes,
            presentation_title=presentation.title
        )
    
    try:
        # Проверяем доступность Gotenberg
        print(f"🔍 Checking Gotenberg service availability...")
        gotenberg_available = await check_gotenberg_health()
        
        if not gotenberg_available:
            gotenberg_url = os.getenv("GOTENBERG_URL", "http://localhost:3000")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"PDF conversion service (Gotenberg) is not available at {gotenberg_url}. "
                       f"Please start Gotenberg using: docker run -d -p 3000:3000 gotenberg/gotenberg:8"
            )
        
        # Конвертируем PPTX в PDF через Gotenberg
        print(f"🔄 Converting PPTX to PDF via Gotenberg...")
        pdf_bytes = await convert_pptx_to_pdf(
            pptx_bytes=pptx_bytes,
            filename=f"{presentation.title}.pptx"
        )
        print(f"✅ PDF conversion successful ({len(pdf_bytes)} bytes)")
        
        # Сохраняем PDF в S3 для кеширования
        try:
            await upload_bytes_to_s3(
                content=pdf_bytes,
                key=pdf_result_key,
                content_type="application/pdf"
            )
            print(f"✅ PDF saved to S3: {pdf_result_key}")
        except Exception as e:
            print(f"⚠️ Could not save PDF to S3: {e}")
        
        # Возвращаем PDF
        from urllib.parse import quote
        filename = f"{safe_filename}.pdf"
        encoded_filename = quote(filename.encode('utf-8'))
        
        pdf_stream = io.BytesIO(pdf_bytes)
        pdf_stream.seek(0)
        
        print(f"📤 Sending PDF: {len(pdf_bytes)} bytes, filename: {filename}")
        
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert PPTX to PDF: {str(exc)}"
        ) from exc
