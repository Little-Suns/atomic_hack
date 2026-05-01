"""
Сервис взаимодействия с LLM через LangChain.
Поддерживает OpenAI-compatible API (OpenAI, Qwen, и другие).
"""

import json
import os
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate


OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://foundation-models.api.cloud.ru/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen3-235B-A22B-Instruct-2507")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))


def get_llm_client(temperature: Optional[float] = None) -> ChatOpenAI:
    """
    Создает клиент для работы с LLM через OpenAI-compatible API.
    
    Args:
        temperature: Температура генерации (0.0 - детерминистично, 1.0 - креативно).
                    Если не указано, используется значение из переменной окружения.
    
    Returns:
        ChatOpenAI: Настроенный клиент LangChain для работы с LLM
        
    Raises:
        RuntimeError: Если не установлен OPENAI_API_KEY
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set OPENAI_API_KEY or pass 'api_key' when creating the client."
        )

    return ChatOpenAI(
        base_url=OPENAI_API_BASE,
        api_key=OPENAI_API_KEY,
        model=MODEL_NAME,
        temperature=temperature if temperature is not None else TEMPERATURE,
    )


SLIDES_GENERATION_SYSTEM_PROMPT = """Ты - эксперт по созданию структуры презентаций.
Твоя задача - создать детальную структуру слайдов на основе:
1. Темы презентации
2. Контекста из предоставленных документов
3. Шаблона презентации (если есть)

Требования:
- Каждый слайд должен иметь четкий title (заголовок)
- description должен содержать подробное описание содержимого слайда (3-5 предложений)
- Слайды должны логически следовать друг за другом
- Первый слайд - титульный
- Последний слайд - заключение/выводы
- Используй контекст из документов для создания релевантного содержимого

Верни результат СТРОГО в JSON формате:
{
  "slides": [
    {
      "position": 0,
      "title": "Заголовок слайда",
      "description": "Детальное описание содержимого слайда"
    }
  ]
}"""


async def generate_slides_structure(
    topic: str,
    num_slides: int,
    context: Optional[str] = None,
    template_design: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Генерирует структуру слайдов с помощью LLM
    
    Args:
        topic: Тема презентации
        num_slides: Количество слайдов
        context: Контекст из документов (RAG)
        template_design: Информация о дизайне шаблона (промпт с описанием дизайна)
        
    Returns:
        Список словарей со структурой слайдов
    """
    llm = get_llm_client(temperature=0.7)
    parser = JsonOutputParser()
    
    # Формируем промпт
    user_message = f"""Тема презентации: {topic}
Количество слайдов: {num_slides}"""
    
    if context:
        user_message += f"\n\nКонтекст из документов:\n{context[:4000]}"  # Ограничиваем размер
    
    if template_design:
        user_message += f"\n\n{template_design}"
    
    user_message += "\n\nСоздай структуру презентации в формате JSON. ОБЯЗАТЕЛЬНО следуй дизайну шаблона если он указан!"
    
    messages = [
        SystemMessage(content=SLIDES_GENERATION_SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    # Вызываем LLM
    response = await llm.ainvoke(messages)
    
    # Парсим ответ
    try:
        # Пытаемся извлечь JSON из ответа
        content = response.content
        if isinstance(content, str):
            # Ищем JSON в ответе
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
            else:
                result = json.loads(content)
        else:
            result = content
            
        slides = result.get("slides", [])
        return slides
    except (json.JSONDecodeError, AttributeError) as e:
        # Fallback: создаем базовую структуру
        return [
            {
                "position": i,
                "title": f"Слайд {i + 1}",
                "description": f"Содержимое слайда {i + 1} по теме '{topic}'"
            }
            for i in range(num_slides)
        ]


SLIDE_CONTENT_GENERATION_PROMPT = """Ты - эксперт по созданию структурированного контента для презентационных слайдов.
Твоя задача - создать структурированное содержимое для одного слайда в JSON формате.

Поддерживаемые типы блоков:
1. **text** - текстовый блок (параграф)
2. **list** - маркированный список
3. **chart** - диаграмма (bar/line/pie)
4. **table** - таблица данных
5. **image** - изображение (генерируется по описанию с помощью AI)

Требования:
- ОБЯЗАТЕЛЬНО: image, chart и table блоки НИКОГДА не должны быть единственными на слайде
- Если используешь image, chart или table - ОБЯЗАТЕЛЬНО добавь text или list блок с пояснением
- text/list блок должен объяснять что показано на изображении/диаграмме/таблице
- Для диаграмм с только ОДНОЙ категорией данных используй или для диграмм, которые показывают РАЗНИЦУ до/после "line" тип (график динамики), а НЕ "bar"
- Для диаграмм с 2+ категориями используй "bar" (столбчатая) или "pie" (круговая)
- Контент должен быть информативным и структурированным
- Не может быть 2 слайдов с одинаковым контентом
- Используй различные типы блоков для лучшего представления данных
- Для числовых данных предпочитай charts и tables
- Для перечислений используй list
- Для описательного текста используй text
- Для визуальных концепций используй image (опиши что должно быть на изображении)
- Используй контекст из документов (если есть) для создания релевантного содержимого
- Используй только один блок типа list, chart, table или image на слайд (наиболее информативный)

Формат ответа (JSON):
{
  "blocks": [
    {
      "type": "text",
      "data": {
        "text": "Текстовое содержимое параграфа"
      }
    },
    {
      "type": "list",
      "data": {
        "items": ["Пункт 1", "Пункт 2", "Пункт 3"]
      }
    },
    {
      "type": "chart",
      "data": {
        "title": "Название диаграммы (опционально)",
        "chart_type": "bar",
        "data": {
          "categories": ["Cat 1", "Cat 2", "Cat 3"],
          "series": [
            {"name": "Series 1", "values": [10, 20, 30]}
          ]
        }
      }
    },
    {
      "type": "table",
      "data": {
        "data": [
          ["Header 1", "Header 2", "Header 3"],
          ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
          ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
        ]
      }
    },
    {
      "type": "image",
      "data": {
        "description": "Детальное описание изображения для генерации (что должно быть на картинке, стиль, композиция)"
      }
    }
  ]
}

Верни ТОЛЬКО JSON без дополнительных объяснений."""


async def generate_slide_content(
    slide_title: str,
    slide_description: str,
    context: Optional[str] = None,
    template_design: Optional[str] = None,
    slide_position: int = 0
) -> str:
    """
    Генерирует структурированное содержимое для конкретного слайда в JSON формате
    
    Args:
        slide_title: Заголовок слайда
        slide_description: Описание слайда
        context: Контекст из документов (RAG)
        template_design: Информация о дизайне шаблона (игнорируется для структурированного контента)
        slide_position: Позиция слайда
        
    Returns:
        JSON строка со структурированным контентом слайда
    """
    llm = get_llm_client(temperature=0.6)
    
    user_message = f"""Создай структурированный контент для слайда #{slide_position + 1}

Заголовок: {slide_title}
Описание: {slide_description}"""
    
    if context:
        user_message += f"\n\nКонтекст из документов:\n{context[:4000]}"
    
    user_message += f"\n\nПозиция слайда: {slide_position}\n\nСоздай структурированный контент для этого слайда в JSON формате."
    user_message += "\n\nВАЖНО: Если в описании есть числовые данные или сравнения - используй chart или table!"
    user_message += "\n\nВерни только валидный JSON без markdown обёрток."
    
    messages = [
        SystemMessage(content=SLIDE_CONTENT_GENERATION_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    response = await llm.ainvoke(messages)
    content = response.content
    
    # Очищаем от markdown обёрток если есть
    if isinstance(content, str):
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    
    # Валидируем JSON
    try:
        parsed_content = json.loads(content)
        blocks = parsed_content.get('blocks', [])
        
        # КРИТИЧНО: Проверяем что если есть визуальные блоки (image/chart/table),
        # то обязательно есть текстовый блок (text/list) с пояснением
        has_visual = any(b.get('type') in ['image', 'chart', 'table'] for b in blocks)
        has_text = any(b.get('type') in ['text', 'list'] for b in blocks)
        
        if has_visual and not has_text:
            print(f"⚠️ LLM сгенерировал только визуальный блок без текста, добавляем text блок")
            # Добавляем текстовый блок с описанием
            text_block = {
                "type": "text",
                "data": {
                    "text": slide_description or "Пояснение к визуальному контенту"
                }
            }
            # Вставляем text блок в начало (перед визуальным контентом)
            blocks.insert(0, text_block)
            parsed_content['blocks'] = blocks
            content = json.dumps(parsed_content, ensure_ascii=False)
        
        # Дополнительная проверка: конвертируем bar -> line для одной категории
        for block in blocks:
            if block.get('type') == 'chart':
                chart_data = block.get('data', {}).get('data', {})
                categories = chart_data.get('categories', [])
                chart_type = block.get('data', {}).get('chart_type', 'bar')
                
                if chart_type in ['bar', 'column'] and len(categories) == 1:
                    print(f"⚠️ LLM сгенерировал bar диаграмму с одной категорией, конвертируем в line")
                    block['data']['chart_type'] = 'line'
                    content = json.dumps(parsed_content, ensure_ascii=False)
        
        return content
    except json.JSONDecodeError:
        # Fallback: создаем простой текстовый блок
        fallback = {
            "blocks": [
                {
                    "type": "text",
                    "data": {
                        "text": slide_description or "Содержимое слайда"
                    }
                }
            ]
        }
        return json.dumps(fallback, ensure_ascii=False)


async def chat_with_assistant(
    message: str,
    presentation_context: Optional[str] = None,
    slides_info: Optional[List[Dict]] = None
) -> str:
    """
    Чат с ассистентом презентаций
    
    Args:
        message: Сообщение пользователя
        presentation_context: Контекст презентации
        slides_info: Информация о слайдах
        
    Returns:
        Ответ ассистента
    """
    llm = get_llm_client(temperature=0.8)
    
    system_prompt = """Ты - помощник по созданию презентаций.
Помогаешь пользователю улучшить презентацию, отвечаешь на вопросы о содержимом,
даёшь советы по структуре и дизайну.

Будь полезным, конкретным и профессиональным."""
    
    user_message = message
    
    if presentation_context:
        user_message = f"Контекст презентации:\n{presentation_context[:2000]}\n\n{message}"
    
    if slides_info:
        slides_summary = "\n".join([
            f"Слайд {s.get('position', i)}: {s.get('title', 'Без названия')}"
            for i, s in enumerate(slides_info[:10])
        ])
        user_message = f"Структура презентации:\n{slides_summary}\n\n{user_message}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content
