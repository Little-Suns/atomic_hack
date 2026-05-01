"""PDF conversion service using Gotenberg API"""
import os
import httpx
from typing import Optional


GOTENBERG_URL = os.getenv("GOTENBERG_URL", "http://localhost:3000")


async def convert_pptx_to_pdf(pptx_bytes: bytes, filename: str = "presentation.pptx") -> bytes:
    """
    Конвертирует PPTX в PDF используя Gotenberg API
    
    Args:
        pptx_bytes: Байты PPTX файла
        filename: Имя файла (для Gotenberg)
        
    Returns:
        PDF файл в байтах
        
    Raises:
        httpx.HTTPError: Если конвертация не удалась
        RuntimeError: Если Gotenberg URL не настроен
    """
    if not GOTENBERG_URL:
        raise RuntimeError(
            "GOTENBERG_URL environment variable is not set. "
            "Please configure Gotenberg API URL in .env file."
        )
    
    # Gotenberg endpoint для конвертации LibreOffice документов
    # https://gotenberg.dev/docs/routes#convert-with-libreoffice
    endpoint = f"{GOTENBERG_URL}/forms/libreoffice/convert"
    
    # Подготавливаем multipart/form-data
    files = {
        'files': (filename, pptx_bytes, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
    }
    
    # Параметры конвертации для презентаций
    # Минимальные параметры - позволяем Gotenberg использовать все настройки из PPTX
    # Это сохранит оригинальные размеры слайдов и не обрежет контент
    data = {
        'nativePageRanges': '1-',  # Все страницы
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                endpoint,
                files=files,
                data=data
            )
            response.raise_for_status()
            
            # Gotenberg возвращает PDF напрямую
            return response.content
            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Gotenberg API returned error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Failed to connect to Gotenberg API at {GOTENBERG_URL}: {str(e)}"
            ) from e


async def check_gotenberg_health() -> bool:
    """
    Проверяет доступность Gotenberg API
    
    Returns:
        True если API доступен, False в противном случае
    """
    if not GOTENBERG_URL:
        return False
    
    health_endpoint = f"{GOTENBERG_URL}/health"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_endpoint)
            return response.status_code == 200
    except Exception:
        return False
