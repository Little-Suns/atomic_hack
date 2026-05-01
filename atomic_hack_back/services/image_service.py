"""Image generation service using Kandinsky API"""
import os
import io
from typing import Optional, Any
import asyncio

try:
    from AsyncKandinsky import FusionBrainApi, ApiApi
except ImportError:
    FusionBrainApi = None
    ApiApi = None


# Environment configuration
KANDINSKY_API_KEY = os.getenv("KANDINSKY_API_KEY", "")
KANDINSKY_SECRET_KEY = os.getenv("KANDINSKY_SECRET_KEY", "")


def get_kandinsky_client() -> Any:
    """
    Создает клиент Kandinsky API
    
    Returns:
        FusionBrainApi client instance
        
    Raises:
        RuntimeError: If AsyncKandinsky is not installed or credentials are missing
    """
    if FusionBrainApi is None or ApiApi is None:
        raise RuntimeError(
            "AsyncKandinsky is not installed. "
            "Install with: pip install AsyncKandinsky"
        )
    
    if not KANDINSKY_API_KEY or not KANDINSKY_SECRET_KEY:
        raise RuntimeError(
            "KANDINSKY_API_KEY and KANDINSKY_SECRET_KEY environment variables are not set. "
            "Set these values in .env file."
        )
    
    return FusionBrainApi(ApiApi(KANDINSKY_API_KEY, KANDINSKY_SECRET_KEY))


async def generate_image_from_description(
    description: str,
    style: str = "DEFAULT",
    art_gpt: bool = True,
    width: int = None,
    height: int = None
) -> bytes:
    """
    Генерирует изображение по текстовому описанию с помощью Kandinsky API
    
    Args:
        description: Текстовое описание изображения (prompt)
        style: Стиль изображения (DEFAULT, ANIME, UHD, etc.)
        art_gpt: Использовать ли автоматическое улучшение промпта (default: True)
        width: Ширина изображения в пиксельях (опционально, по умолчанию API выберет)
        height: Высота изображения в пиксельях (опционально, по умолчанию API выберет)
        
    Returns:
        bytes: Содержимое изображения в формате PNG
        
    Raises:
        RuntimeError: If image generation fails
    """
    try:
        model = get_kandinsky_client()
        
        if width and height:
            print(f"🎨 Генерация изображения: '{description[:100]}...' (размер: {width}x{height})")
        else:
            print(f"🎨 Генерация изображения: '{description[:100]}...'")
        
        # Подготавливаем параметры для text2image
        # Передаем width/height ТОЛЬКО если они установлены (не None)
        text2image_kwargs = {
            'style': style,
            'art_gpt': art_gpt
        }
        
        # Добавляем width и height только если они имеют значение
        if width is not None:
            text2image_kwargs['width'] = width
        if height is not None:
            text2image_kwargs['height'] = height
        
        # Генерируем изображение используя text2image
        # art_gpt=True улучшает качество автоматически оптимизируя промпт
        result = await model.text2image(description, **text2image_kwargs)
        
        # result.getvalue() возвращает bytes изображения
        image_bytes = result.getvalue()
        
        print(f"✅ Изображение сгенерировано ({len(image_bytes)} bytes)")
        return image_bytes
        
    except ValueError as e:
        print(f"❌ Ошибка генерации изображения (ValueError): {str(e)}")
        raise RuntimeError(f"Failed to generate image: {str(e)}") from e
    except Exception as e:
        print(f"❌ Ошибка генерации изображения: {type(e).__name__}: {str(e)}")
        raise RuntimeError(f"Failed to generate image: {str(e)}") from e


async def generate_image_with_retry(
    description: str,
    style: str = "DEFAULT",
    art_gpt: bool = True,
    width: int = None,
    height: int = None,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Генерирует изображение с повторными попытками при ошибках
    
    Args:
        description: Текстовое описание изображения
        style: Стиль изображения (DEFAULT, ANIME, UHD, etc.)
        art_gpt: Использовать ли автоматическое улучшение промпта
        width: Ширина изображения в пиксельях (опционально)
        height: Высота изображения в пиксельях (опционально)
        max_retries: Максимальное количество попыток
        
    Returns:
        bytes: Содержимое изображения или None при неудаче
    """
    print(f"[generate_image_with_retry] Начинаем с параметрами: width={width}, height={height}, max_retries={max_retries}")
    
    for attempt in range(max_retries):
        try:
            print(f"[generate_image_with_retry] Попытка {attempt + 1}/{max_retries}")
            result = await generate_image_from_description(
                description=description,
                style=style,
                art_gpt=art_gpt,
                width=width,
                height=height
            )
            print(f"[generate_image_with_retry] Успешно! Возвращаем результат ({len(result)} bytes)")
            return result
        except Exception as e:
            print(f"⚠️ Попытка {attempt + 1}/{max_retries} не удалась: {str(e)}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            
            if attempt < max_retries - 1:
                # Ждем перед следующей попыткой (exponential backoff)
                wait_time = 2 ** attempt
                print(f"⏳ Ожидание {wait_time}s перед следующей попыткой...")
                await asyncio.sleep(wait_time)
            else:
                print(f"❌ Все {max_retries} попытки не удались")
                return None
    
    print(f"[generate_image_with_retry] Выход из цикла, возвращаем None")
    return None


def check_kandinsky_configuration() -> dict:
    """
    Проверяет конфигурацию Kandinsky API
    
    Returns:
        dict с информацией о конфигурации
    """
    config_status = {
        "configured": False,
        "has_api_key": bool(KANDINSKY_API_KEY),
        "has_secret_key": bool(KANDINSKY_SECRET_KEY),
        "asynckandinsky_installed": FusionBrainApi is not None and ApiApi is not None,
        "errors": []
    }
    
    if not FusionBrainApi or not ApiApi:
        config_status["errors"].append("asynckandinsky not installed")
        return config_status
    
    if not KANDINSKY_API_KEY:
        config_status["errors"].append("KANDINSKY_API_KEY not set")
    
    if not KANDINSKY_SECRET_KEY:
        config_status["errors"].append("KANDINSKY_SECRET_KEY not set")
    
    if not config_status["errors"]:
        config_status["configured"] = True
    
    return config_status
