import random
import asyncio
from typing import List, Dict, Any
import os
import io

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models.presentation import Presentation
from schemas import PresentationRead, SlideRead


def _generate_random_id(db: Session) -> int:
    for _ in range(10):
        candidate = random.randint(100000, 999999)
        if not db.query(Presentation).filter(Presentation.id == candidate).first():
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate unique presentation id")

router = APIRouter()


@router.get("/getPresentations", response_model=List[PresentationRead])
async def get_presentations(user_id: int, db: Session = Depends(get_db)):
    presentations = (
        db.query(Presentation)
        .options(selectinload(Presentation.slides))
        .filter(Presentation.user_id == user_id)
        .order_by(Presentation.id)
        .all()
    )
    
    return [
        PresentationRead(
            id=p.id,
            title=p.title,
            user_id=p.user_id,
            template_bucket_id=p.template_bucket_id,
            context_files=p.context_files,
            rag_id=p.rag_id,
            slides=p.slides,
        )
        for p in presentations
    ]

@router.post("/newPresentation", response_model=PresentationRead, status_code=status.HTTP_201_CREATED)
def new_presentation(user_id: int, title: str, db: Session = Depends(get_db)):
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")
    
    # Проверяем существование пользователя, создаем дефолтного если нужно
    from models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Создаем дефолтного пользователя
        user = User(
            id=user_id,
            email=f"user_{user_id}@example.com",
            hashed_password="default_password_hash"  # Placeholder, not for real auth
        )
        db.add(user)
        db.commit()
        print(f"✅ Created default user with id={user_id}")

    presentation = Presentation(
        id=_generate_random_id(db),
        title=title,
        user_id=user_id,
    )
    db.add(presentation)
    db.commit()
    db.refresh(presentation)
    return presentation

@router.delete("/deletePresentation")
async def delete_presentation(presentation_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Удаляет презентацию и все связанные слайды, её RAG коллекцию из Qdrant,
    а также все файлы презентации в S3
    """
    from services.rag_service import delete_rag_collection
    from services.s3_service import delete_prefix_from_s3
    
    presentation = db.query(Presentation).filter(
        Presentation.id == presentation_id,
        Presentation.user_id == user_id
    ).first()
    
    if not presentation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation not found or access denied"
        )
    
    # Удаляем RAG коллекцию из Qdrant если она существует
    rag_id = presentation.rag_id
    if rag_id:
        try:
            success = await delete_rag_collection(rag_id)
            if success:
                print(f"✅ Deleted RAG collection: {rag_id}")
            else:
                print(f"⚠️ Failed to delete RAG collection {rag_id}: collection may not exist")
        except Exception as e:
            print(f"⚠️ Exception while deleting RAG collection {rag_id}: {e}")
            # Не прерываем процесс удаления презентации если удаление RAG не удалось
    
    # Удаляем директорию презентации в S3
    s3_prefix = f"presentations/{presentation_id}/"
    s3_deleted_count = 0
    try:
        s3_deleted_count = await delete_prefix_from_s3(s3_prefix)
        print(f"✅ Deleted S3 directory: {s3_prefix} ({s3_deleted_count} files)")
    except Exception as e:
        print(f"⚠️ Exception while deleting S3 directory {s3_prefix}: {e}")
        # Не прерываем процесс удаления презентации если удаление S3 не удалось
    
    # Удаляем саму презентацию
    db.delete(presentation)
    db.commit()
    
    return {
        "message": "Presentation deleted successfully",
        "presentation_id": presentation_id,
        "rag_collection_deleted": bool(rag_id),
        "s3_files_deleted": s3_deleted_count
    }

def _get_presentation_or_404(db: Session, presentation_id: int) -> Presentation:
    presentation = (
        db.query(Presentation)
        .options(selectinload(Presentation.slides))
        .filter(Presentation.id == presentation_id)
        .first()
    )
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    return presentation


@router.post("/changeTitle", response_model=PresentationRead)
def change_title(presentation_id: int, new_title: str, db: Session = Depends(get_db)):
    if not new_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New title is required")

    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    presentation.title = new_title
    db.commit()
    db.refresh(presentation)
    return presentation

@router.get("/getSlidesInfo", response_model=List[SlideRead])
def get_slides_info(presentation_id: int, db: Session = Depends(get_db)):
    presentation = _get_presentation_or_404(db, presentation_id)
    return presentation.slides


@router.get("/getPresentation", response_model=PresentationRead)
async def get_presentation(presentation_id: int, db: Session = Depends(get_db)):
    """
    Получает полную информацию о презентации включая все её слайды.
    
    Args:
        presentation_id: ID презентации
        
    Returns:
        Полная информация о презентации со всеми слайдами
    """
    presentation = _get_presentation_or_404(db, presentation_id)

    return PresentationRead(
        id=presentation.id,
        title=presentation.title,
        user_id=presentation.user_id,
        template_bucket_id=presentation.template_bucket_id,
        context_files=presentation.context_files,
        rag_id=presentation.rag_id,
        slides=presentation.slides,
    )


async def _generate_slide_content_background(presentation_id: int, db: Session):
    """
    Фоновая задача для генерации структурированного контента для каждого слайда.
    """
    from services.llm_service import generate_slide_content
    from services.rag_service import search_context
    from models.slide import Slide
    import json

    try:
        presentation = _get_presentation_or_404(db, presentation_id)
        
        if not presentation.slides:
            print(f"Warning: No slides found for presentation {presentation_id} in background task.")
            return
        
        semaphore = asyncio.Semaphore(3)
        generated_count = 0

        async def generate_and_update_slide(slide):
            nonlocal generated_count
            async with semaphore:
                context = None
                if presentation.rag_id:
                    try:
                        search_query = f"{slide.title} {slide.description or ''}"
                        context = await search_context(presentation.rag_id, search_query, top_k=3)
                    except Exception:
                        context = None
                
                try:
                    content_json = await generate_slide_content(
                        slide_title=slide.title,
                        slide_description=slide.description or "",
                        context=context,
                        template_design=None,
                        slide_position=slide.position
                    )
                    slide.content_json = content_json
                    generated_count += 1
                    db.commit()
                except Exception as e:
                    print(f"Warning: Failed to generate content for slide {slide.id}: {e}")
                    # Fallback: простой текстовый блок
                    fallback = {
                        "blocks": [
                            {
                                "type": "text",
                                "data": {
                                    "text": slide.description or "Содержимое слайда"
                                }
                            }
                        ]
                    }
                    slide.content_json = json.dumps(fallback, ensure_ascii=False)
                    db.commit()
        
        tasks = [generate_and_update_slide(slide) for slide in sorted(presentation.slides, key=lambda s: s.position)]
        await asyncio.gather(*tasks)
        
        db.commit()
        
        # Инвалидируем кеш PPTX и PDF в S3 (т.к. контент изменился)
        try:
            from services.s3_service import delete_from_s3
            from routers.files import sanitize_filename
            safe_title = sanitize_filename(presentation.title)
            pptx_key = f"presentations/{presentation_id}/result/{safe_title}.pptx"
            pdf_key = f"presentations/{presentation_id}/result/{safe_title}.pdf"
            
            await delete_from_s3(pptx_key)
            await delete_from_s3(pdf_key)
            print(f"🗑️ Invalidated S3 cache for presentation {presentation_id}")
        except Exception as cache_err:
            print(f"⚠️ Could not invalidate S3 cache: {cache_err}")
        
        print(f"✅ Background content generation finished: {generated_count}/{len(presentation.slides)} slides for presentation {presentation_id}.")

    except Exception as e:
        print(f"Error in background content generation for presentation {presentation_id}: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/generateSlideContent", status_code=status.HTTP_200_OK)
async def generate_slide_content_endpoint(
    presentation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Запускает фоновую задачу для генерации структурированного контента для каждого слайда.
    """
    _get_presentation_or_404(db, presentation_id) # Проверяем, что презентация существует
    
    background_tasks.add_task(
        _generate_slide_content_background,
        presentation_id=presentation_id,
        db=next(get_db())
    )
    
    return {"message": "Slide content generation started in the background."}


async def _generate_slides_info_background(
    presentation_id: int,
    topic: str,
    num_slides: int,
    use_context: bool,
    db: Session
):
    """
    Фоновая задача для генерации структуры слайдов.
    """
    from services.llm_service import generate_slides_structure
    from services.rag_service import search_context
    from models.slide import Slide
    import json

    try:
        presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
        if not presentation:
            print(f"Error: Presentation {presentation_id} not found in background task.")
            return

        # Получаем контекст из RAG если есть
        context = None
        if use_context and presentation.rag_id:
            try:
                context = await search_context(presentation.rag_id, topic, top_k=5)
            except Exception as e:
                print(f"Warning: Could not load RAG context for presentation {presentation_id}: {e}")
        
        # Генерируем структуру слайдов
        slides_data = await generate_slides_structure(
            topic=topic,
            num_slides=num_slides,
            context=context,
            template_design=None
        )
        
        # Создаем слайды в БД
        for slide_info in slides_data:
            slide = Slide(
                presentation_id=presentation_id,
                position=slide_info.get("position", 0),
                title=slide_info.get("title", ""),
                description=slide_info.get("description", "")
            )
            db.add(slide)
        
        db.commit()
        print(f"✅ Background slide generation finished: {len(slides_data)} slides created for presentation {presentation_id}.")

    except Exception as e:
        print(f"Error in background slide generation for presentation {presentation_id}: {e}")
        db.rollback()
    finally:
        db.close()


@router.get("/getPresentationContent")
async def get_presentation_content(presentation_id: int, db: Session = Depends(get_db)):
    """
    Возвращает сгенерированный структурированный контент слайдов из БД
    """
    presentation = _get_presentation_or_404(db, presentation_id)
    
    slides_content = []
    for slide in sorted(presentation.slides, key=lambda s: s.position):
        slides_content.append({
            "id": slide.id,
            "position": slide.position,
            "title": slide.title,
            "content_json": slide.content_json
        })
    
    has_content = any(slide.content_json for slide in presentation.slides)
    
    return {
        "presentation_id": presentation_id,
        "slides": slides_content,
        "has_content": has_content
    }


@router.get("/getContent")
def get_content(presId: int, db: Session = Depends(get_db)):
    """
    Альтернативный эндпоинт для polling - возвращает слайды в формате [{Title, Content}]
    Использует presId вместо presentation_id для совместимости с фронтендом.
    Content теперь содержит content_json вместо HTML.
    """
    presentation = _get_presentation_or_404(db, presId)
    
    # Формируем ответ в формате [{Title, Content}]
    slides_data = []
    for slide in sorted(presentation.slides, key=lambda s: s.position):
        slides_data.append({
            "Title": slide.title or "",
            "Content": slide.content_json or ""
        })
    
    return slides_data


@router.post("/generateSlidesInfo", status_code=status.HTTP_200_OK)
async def generate_slides_info(
    presentation_id: int,
    topic: str,
    background_tasks: BackgroundTasks,
    num_slides: int = 10,
    use_context: bool = True,
    db: Session = Depends(get_db)
):
    """
    Запускает фоновую задачу для генерации структуры слайдов.
    Полностью удаляет все старые слайды перед началом.
    """
    from models.slide import Slide
    
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    
    # Удаляем старые слайды немедленно
    db.query(Slide).filter(Slide.presentation_id == presentation_id).delete()
    db.commit()
    
    # Запускаем генерацию в фоне
    background_tasks.add_task(
        _generate_slides_info_background,
        presentation_id=presentation_id,
        topic=topic,
        num_slides=num_slides,
        use_context=use_context,
        db=next(get_db()) # Передаем новую сессию в фоновую задачу
    )
    
    return {"message": "Slide generation started in the background."}


async def _regenerate_slides_content(
    presentation_id: int,
    slide_positions: List[int],
    db: Session
):
    """
    Фоновая задача для перегенерации content_json только для указанных слайдов.
    Используется после изменения слайдов через presentationAssistantMessage.
    После успешной регенерации - удаляет кеш из S3.
    """
    from services.llm_service import generate_slide_content
    from services.rag_service import search_context
    from services.s3_service import delete_from_s3
    from models.slide import Slide
    import json

    try:
        presentation = _get_presentation_or_404(db, presentation_id)
        
        # Фильтруем только слайды которые нужно перегенерировать
        slides_to_regenerate = [
            s for s in presentation.slides 
            if s.position in slide_positions
        ]
        
        if not slides_to_regenerate:
            print(f"Warning: No slides to regenerate for presentation {presentation_id}")
            return
        
        print(f"🔄 Starting content regeneration for {len(slides_to_regenerate)} slides in presentation {presentation_id}")
        
        semaphore = asyncio.Semaphore(3)
        regenerated_count = 0

        async def regenerate_slide(slide):
            nonlocal regenerated_count
            async with semaphore:
                context = None
                if presentation.rag_id:
                    try:
                        search_query = f"{slide.title} {slide.description or ''}"
                        context = await search_context(presentation.rag_id, search_query, top_k=3)
                    except Exception:
                        context = None
                
                try:
                    content_json = await generate_slide_content(
                        slide_title=slide.title,
                        slide_description=slide.description or "",
                        context=context,
                        template_design=None,
                        slide_position=slide.position
                    )
                    slide.content_json = content_json
                    regenerated_count += 1
                    db.commit()
                    print(f"✅ Regenerated slide {slide.position}: {slide.title}")
                except Exception as e:
                    print(f"⚠️ Failed to regenerate content for slide {slide.id}: {e}")
                    # Fallback: простой текстовый блок
                    fallback = {
                        "blocks": [
                            {
                                "type": "text",
                                "data": {
                                    "text": slide.description or "Содержимое слайда"
                                }
                            }
                        ]
                    }
                    slide.content_json = json.dumps(fallback, ensure_ascii=False)
                    db.commit()
        
        tasks = [regenerate_slide(slide) for slide in slides_to_regenerate]
        await asyncio.gather(*tasks)
        
        db.commit()
        print(f"✅ Content regeneration finished: {regenerated_count}/{len(slides_to_regenerate)} slides for presentation {presentation_id}")
        
        # Удаляем кеш PPTX и PDF из S3 ПОСЛЕ успешной регенерации контента
        from routers.files import sanitize_filename
        safe_title = sanitize_filename(presentation.title)
        pptx_key = f"presentations/{presentation_id}/result/{safe_title}.pptx"
        pdf_key = f"presentations/{presentation_id}/result/{safe_title}.pdf"
        try:
            await delete_from_s3(pptx_key)
            await delete_from_s3(pdf_key)
            print(f"🗑️ Invalidated S3 cache for presentation {presentation_id} after content regeneration")
        except Exception as cache_err:
            print(f"⚠️ Could not invalidate S3 cache: {cache_err}")

    except Exception as e:
        print(f"❌ Error in content regeneration for presentation {presentation_id}: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/changeSlidesInfo")
async def change_slides_info(
    presentation_id: int,
    slides_info: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Обновляет информацию (title, description, position) для всех слайдов презентации.
    Ожидает список объектов вида: [{"id": 1, "title": "...", "description": "...", "position": 1}, ...]
    Использует ID для поиска слайдов, что позволяет корректно обрабатывать пересортировку.
    
    Возможные ID:
    - number: существующий слайд из БД
    - null/None: новый слайд (будет создан)
    - string: попытается распарсить как число
    """
    from models.slide import Slide

    # Проверяем существование презентации
    presentation = db.query(Presentation).options(selectinload(Presentation.slides)).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    # Удаляем кеш PPTX и PDF из S3, так как структура изменилась
    from routers.files import sanitize_filename
    safe_title = sanitize_filename(presentation.title)
    pptx_key = f"presentations/{presentation_id}/result/{safe_title}.pptx"
    pdf_key = f"presentations/{presentation_id}/result/{safe_title}.pdf"
    try:
        from services.s3_service import delete_from_s3
        await delete_from_s3(pptx_key)
        await delete_from_s3(pdf_key)
        print(f"🗑️ Deleted S3 cache for presentation {presentation_id}")
    except Exception as e:
        print(f"⚠️ Could not delete S3 cache: {e}")

    # Получаем существующие слайды и создаем карту id -> slide
    existing_slides_map = {s.id: s for s in presentation.slides}
    
    # Парсим входящие IDs и создаем множество валидных ID существующих слайдов
    incoming_slide_ids = set()
    for slide_info in slides_info:
        slide_id = slide_info.get("id")
        
        # Пропускаем None/null/empty значения (это новые слайды)
        if slide_id is None or slide_id == "":
            continue
        
        # Пытаемся конвертировать в int
        try:
            slide_id_int = int(slide_id) if not isinstance(slide_id, int) else slide_id
            incoming_slide_ids.add(slide_id_int)
        except (ValueError, TypeError):
            # Если не удалось распарсить, пропускаем
            print(f"⚠️ Invalid slide ID format: {slide_id}")
            continue

    # Удаляем слайды, которых нет в новом списке
    deleted_count = 0
    for slide_id, slide in existing_slides_map.items():
        if slide_id not in incoming_slide_ids:
            print(f"🗑️ Deleting slide ID {slide_id} (Position {slide.position}): {slide.title}")
            db.delete(slide)
            deleted_count += 1
    
    if deleted_count > 0:
        db.flush()  # Flush для освобождения ID
        print(f"🗑️ Deleted {deleted_count} slides from presentation {presentation_id}")

    # Обновляем и создаем слайды
    updated_slides_count = 0
    created_slides_count = 0
    
    for slide_info in slides_info:
        # Валидируем обязательные поля
        position = slide_info.get("position")
        title = slide_info.get("title", "").strip()
        description = slide_info.get("description", "").strip()

        if position is None or not title:
            print(f"⚠️ Skipping invalid slide info (missing position or title): {slide_info}")
            continue

        # Парсим ID
        slide_id = slide_info.get("id")
        slide_id_int = None
        
        if slide_id is not None and slide_id != "":
            try:
                slide_id_int = int(slide_id) if not isinstance(slide_id, int) else slide_id
            except (ValueError, TypeError):
                pass

        # Ищем существующий слайд по ID
        slide = existing_slides_map.get(slide_id_int) if slide_id_int else None
        
        if slide:
            # Обновляем существующий слайд
            slide.title = title
            slide.description = description
            slide.position = int(position)
            updated_slides_count += 1
        else:
            # Создаем новый слайд
            # (Например, если слайд был добавлен на фронтенде, ID не предоставлен)
            new_slide = Slide(
                presentation_id=presentation_id,
                position=int(position),
                title=title,
                description=description
            )
            db.add(new_slide)
            created_slides_count += 1
            print(f"✨ Creating new slide at position {position}: {title}")

    db.commit()
    
    print(f"✅ change_slides_info completed: {updated_slides_count} updated, {created_slides_count} created, {deleted_count} deleted")

    return {
        "presentation_id": presentation_id,
        "updated_count": updated_slides_count,
        "created_count": created_slides_count,
        "deleted_count": deleted_count,
        "message": "Slides info updated successfully"
    }


@router.post("/presentationAssistantMessage")
async def presentation_assistant_message(
    presentation_id: int,
    message: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Исправляет/переписывает конкретные слайды презентации по инструкции пользователя.
    Анализирует content_json, description и title для определения слайдов к изменению.
    
    Примеры инструкций:
    - "сделай слайд 3 более детальным"
    - "перепиши первые два слайда в более формальном стиле"
    - "замени 'Росатом плохая компания' на 'Росатом хорошая компания'"
    - "упрости все слайды с техническими деталями"
    """
    from services.llm_service import get_llm_client, generate_slide_content
    from services.rag_service import search_context
    from langchain_core.messages import SystemMessage, HumanMessage
    from models.slide import Slide
    import json
    
    # Проверяем презентацию
    presentation = (
        db.query(Presentation)
        .options(selectinload(Presentation.slides))
        .filter(Presentation.id == presentation_id)
        .first()
    )
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    
    if not presentation.slides:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No slides found in presentation"
        )
    
    # Формируем контекст с ПОЛНОЙ информацией о всех слайдах (включая content_json)
    slides_context = "Текущие слайды презентации:\n\n"
    for slide in sorted(presentation.slides, key=lambda s: s.position):
        slides_context += f"Слайд {slide.position}:\n"
        slides_context += f"  Заголовок: {slide.title}\n"
        slides_context += f"  Описание: {slide.description or 'Нет описания'}\n"
        
        # Добавляем краткое представление content_json для анализа
        if slide.content_json:
            try:
                content_data = json.loads(slide.content_json)
                blocks = content_data.get("blocks", [])
                content_preview = []
                for block in blocks[:3]:  # Показываем первые 3 блока
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text = block.get("data", {}).get("text", "")[:100]
                        content_preview.append(f"[text]: {text}")
                    elif block_type == "list":
                        items = block.get("data", {}).get("items", [])
                        content_preview.append(f"[list]: {', '.join(items[:3])}")
                    elif block_type == "chart":
                        chart_type = block.get("data", {}).get("chart_type", "")
                        content_preview.append(f"[chart: {chart_type}]")
                    elif block_type == "table":
                        content_preview.append("[table]")
                
                if content_preview:
                    slides_context += f"  Контент: {'; '.join(content_preview)}\n"
            except:
                pass
        
        slides_context += "\n"
    
    # Получаем RAG контекст если есть
    rag_context = None
    if presentation.rag_id:
        try:
            rag_context = await search_context(presentation.rag_id, message, top_k=3)
        except Exception:
            pass
    
    # Промпт для LLM с анализом контента
    system_prompt = """Ты - эксперт по редактированию презентаций.
Твоя задача - проанализировать слайды и определить какие нужно изменить согласно инструкции.

ПРАВИЛА:
1. Анализируй все слайды - и заголовки, и описания, и контент
2. Если указаны конкретные номера - изменяй только их
3. Если нужна замена текста (X на Y) - найди слайды где встречается X
4. Для каждого слайда к изменению: создай НОВЫЙ title и подробное description

ОТВЕТ ДОЛЖЕН БЫТЬ ИСКЛЮЧИТЕЛЬНО JSON, БЕЗ ОБЪЯСНЕНИЙ И КОММЕНТАРИЕВ:

{
  "slides_to_update": [
    {
      "position": 1,
      "title": "Новый заголовок",
      "description": "Подробное описание для слайда"
    }
  ]
}

ТОЛЬКО JSON. БЕЗ ТЕКСТА ДО И ПОСЛЕ JSON."""
    
    user_message = f"""{slides_context}

Инструкция пользователя: {message}"""
    
    if rag_context:
        user_message += f"\n\nКонтекст из документов:\n{rag_context[:2000]}"
    
    user_message += "\n\nВерни ТОЛЬКО JSON без объяснений."
    
    # Вызываем LLM для определения слайдов
    try:
        llm = get_llm_client(temperature=0.7)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = await llm.ainvoke(messages)
        
        # Парсим ответ - ищем JSON в ответе
        content = response.content
        result = None
        
        if isinstance(content, str):
            # Пытаемся найти JSON объект в ответе
            content = content.strip()
            
            # Сначала пытаемся распарсить весь контент как JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Если не сработало, ищем JSON блок внутри текста
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
        
        if not result:
            print(f"⚠️ Не удалось распарсить ответ LLM: {content[:200]}")
            return {
                "presentation_id": presentation_id,
                "message": "Ошибка парсинга ответа. Попробуйте переформулировать инструкцию.",
                "updated_slides": []
            }
        
        slides_to_update = result.get("slides_to_update", [])
        
        if not slides_to_update:
            return {
                "presentation_id": presentation_id,
                "message": "Не удалось определить какие слайды нужно изменить. Попробуйте уточнить инструкцию.",
                "updated_slides": []
            }
        
        # Обновляем title и description слайдов в БД
        updated_slides = []
        slides_to_regenerate = []
        
        for slide_update in slides_to_update:
            position = slide_update.get("position")
            new_title = slide_update.get("title")
            new_description = slide_update.get("description")
            
            # Находим слайд по position
            slide = next((s for s in presentation.slides if s.position == position), None)
            if slide:
                slide.title = new_title
                slide.description = new_description
                # Сбрасываем content_json - будет перегенерирован
                slide.content_json = None
                
                updated_slides.append({
                    "position": position,
                    "title": new_title,
                    "description": new_description
                })
                slides_to_regenerate.append(slide)
        
        db.commit()
        
        # Запускаем перегенерацию content_json для измененных слайдов в фоновой задаче
        # Кеш PPTX и PDF будут удалены ПОСЛЕ успешной регенерации контента
        if slides_to_regenerate:
            background_tasks.add_task(
                _regenerate_slides_content,
                presentation_id=presentation_id,
                slide_positions=[s.position for s in slides_to_regenerate],
                db=next(get_db())
            )
        
        return {
            "presentation_id": presentation_id,
            "message": f"Обновлено слайдов: {len(updated_slides)}. Контент перегенерируется в фоне.",
            "updated_slides": updated_slides
        }
    
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process instruction: {exc}"
        ) from exc
