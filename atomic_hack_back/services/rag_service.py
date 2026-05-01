"""RAG service using Qdrant and LangChain"""
import os
import uuid
import logging
from typing import List, Optional
from pathlib import Path
import asyncio

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
import pypandoc
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_unstructured import UnstructuredLoader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from services.ocr_service import ocr_file_with_qwen_vl, is_ocr_enabled

logger = logging.getLogger("app.rag")

# Конфигурация
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "1000"))
COLLECTION_PREFIX = "presentations"

# Размерности для разных моделей эмбеддингов
EMBEDDING_DIMENSIONS = {
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Cloud.ru / Qwen
    "Qwen/Qwen3-Embedding-0.6B": 1024,
    "BAAI/bge-m3": 1024,
    "intfloat/multilingual-e5-large": 1024,
    "intfloat/multilingual-e5-large-instruct": 1024,
}


def get_embeddings() -> OpenAIEmbeddings:
    """Создает embeddings клиент"""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set OPENAI_API_KEY or pass 'api_key' when creating the client."
        )
    return OpenAIEmbeddings(
        base_url=OPENAI_API_BASE,
        api_key=OPENAI_API_KEY,
        model=EMBEDDING_MODEL,
    )


def get_qdrant_client() -> QdrantClient:
    """Создает Qdrant клиент"""
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL  )


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """
    Создает text splitter с умным разбиением на чанки
    LangChain автоматически учитывает структуру документа
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=[
            "\n\n",  # Разделяем по параграфам
            "\n",    # Затем по строкам
            ". ",    # Затем по предложениям
            " ",     # Наконец по словам
            ""
        ],
        is_separator_regex=False,
    )


async def load_document_from_file(file_path: str, file_type: str) -> List[Document]:
    """
    Загружает документ используя подходящий LangChain loader.
    Для PDF и DOCX конвертирует в Markdown.
    При неудаче или недостаточном количестве текста использует OCR если он включен.
    
    Args:
        file_path: Путь к файлу
        file_type: Тип файла (pdf, docx, txt, etc.)
        
    Returns:
        Список Document объектов
        
    Raises:
        ValueError: Если не удалось загрузить документ даже с OCR
    """
    file_type = file_type.lower()
    
    try:
        if file_type == "pdf":
            # Сначала пытаемся обычное извлечение текста
            try:
                logger.debug(f"Attempting standard text extraction from PDF: {file_path}")
                loader = PyPDFLoader(file_path)
                documents = await asyncio.to_thread(loader.load)
                
                # Проверяем, что текст был успешно извлечен и его достаточно
                total_text_length = sum(len(doc.page_content.strip()) for doc in documents)
                
                if documents and total_text_length > MIN_TEXT_LENGTH:
                    logger.info(f"Successfully extracted {total_text_length} chars from PDF using standard loader")
                    return documents
                else:
                    if total_text_length <= MIN_TEXT_LENGTH:
                        logger.warning(f"Extracted text too short ({total_text_length} chars < {MIN_TEXT_LENGTH} min), trying OCR")
                    else:
                        logger.warning(f"No text extracted from PDF using standard loader, trying OCR")
                    raise ValueError("Insufficient text extracted from PDF")
                    
            except Exception as e:
                logger.warning(f"Standard PDF extraction failed or text too short: {e}")
                
                # Если стандартное извлечение не работает или текста слишком мало, используем OCR
                if is_ocr_enabled():
                    try:
                        logger.info(f"Using OCR to extract text from PDF")
                        text_content = await ocr_file_with_qwen_vl(file_path, "pdf")
                        if text_content and len(text_content.strip()) > MIN_TEXT_LENGTH:
                            logger.info(f"OCR successfully extracted {len(text_content)} chars from PDF")
                            return [Document(page_content=text_content, metadata={"source": file_path, "extraction_method": "ocr"})]
                        else:
                            logger.warning(f"OCR extracted insufficient text ({len(text_content) if text_content else 0} chars)")
                            raise ValueError("OCR extracted insufficient text")
                    except Exception as ocr_error:
                        logger.error(f"OCR extraction failed: {ocr_error}")
                        raise ValueError(f"Both standard extraction and OCR failed for PDF: {e}, OCR error: {ocr_error}")
                else:
                    logger.error(f"Standard extraction failed and OCR is disabled")
                    raise ValueError(f"Failed to load PDF document (OCR is disabled): {e}")

        elif file_type in ["docx", "doc"]:
            # Пытаемся конвертировать документ
            try:
                logger.debug(f"Attempting standard extraction from DOCX: {file_path}")
                markdown_text = await asyncio.to_thread(
                    pypandoc.convert_file, file_path, "md"
                )
                if markdown_text and len(markdown_text.strip()) > MIN_TEXT_LENGTH:
                    logger.info(f"Successfully extracted {len(markdown_text)} chars from DOCX")
                    return [Document(page_content=markdown_text, metadata={"source": file_path})]
                else:
                    if markdown_text:
                        logger.warning(f"Extracted text too short ({len(markdown_text)} chars < {MIN_TEXT_LENGTH} min), trying OCR")
                    else:
                        logger.warning(f"No text extracted from DOCX")
                    raise ValueError("Insufficient text extracted from DOCX")
            except Exception as e:
                logger.warning(f"Standard DOCX extraction failed or text too short: {e}")
                
                # Если стандартное извлечение не работает или текста слишком мало, используем OCR
                if is_ocr_enabled():
                    try:
                        logger.info(f"Using OCR to extract text from DOCX")
                        text_content = await ocr_file_with_qwen_vl(file_path, "docx")
                        if text_content and len(text_content.strip()) > MIN_TEXT_LENGTH:
                            logger.info(f"OCR successfully extracted {len(text_content)} chars from DOCX")
                            return [Document(page_content=text_content, metadata={"source": file_path, "extraction_method": "ocr"})]
                        else:
                            logger.warning(f"OCR extracted insufficient text from DOCX")
                            raise ValueError("OCR extracted insufficient text")
                    except Exception as ocr_error:
                        logger.error(f"OCR extraction failed: {ocr_error}")
                        raise ValueError(f"Both standard extraction and OCR failed for DOCX: {e}, OCR error: {ocr_error}")
                else:
                    logger.error(f"Standard extraction failed and OCR is disabled")
                    raise ValueError(f"Failed to load DOCX document (OCR is disabled): {e}")

        elif file_type == "txt":
            logger.debug(f"Loading TXT file: {file_path}")
            loader = TextLoader(file_path)
            documents = await asyncio.to_thread(loader.load)
            logger.info(f"Successfully loaded TXT file")
            return documents
            
        else:
            # Для остальных используем UnstructuredLoader
            logger.debug(f"Attempting UnstructuredLoader for {file_type}: {file_path}")
            loader = UnstructuredLoader(file_path)
            documents = await asyncio.to_thread(loader.load)
            total_text_length = sum(len(doc.page_content.strip()) for doc in documents)
            
            if total_text_length > MIN_TEXT_LENGTH:
                logger.info(f"Successfully loaded {file_type} file with {total_text_length} chars")
                return documents
            else:
                logger.warning(f"Loaded {file_type} file but text too short ({total_text_length} chars), trying OCR")
                raise ValueError("Insufficient text extracted")
            
    except Exception as e:
        logger.error(f"Document loading failed: {e}")
        # Fallback на OCR для любого типа файла если включен
        try:
            if is_ocr_enabled():
                logger.warning(f"Attempting fallback OCR for {file_type}")
                text_content = await ocr_file_with_qwen_vl(file_path, file_type)
                if text_content and len(text_content.strip()) > MIN_TEXT_LENGTH:
                    logger.info(f"Fallback OCR succeeded: extracted {len(text_content)} chars")
                    return [Document(page_content=text_content, metadata={"source": file_path, "extraction_method": "ocr"})]
            
            # Если OCR не включен или не сработал, пробуем UnstructuredLoader
            logger.warning(f"Attempting fallback UnstructuredLoader")
            loader = UnstructuredLoader(file_path)
            documents = await asyncio.to_thread(loader.load)
            logger.info(f"Fallback loader succeeded")
            return documents
        except Exception as fallback_error:
            logger.error(f"Fallback loader also failed: {fallback_error}")
            raise ValueError(f"Failed to load document: {e}. Fallback error: {fallback_error}")


async def create_rag_collection(
    presentation_id: int,
    file_path: str,
    file_type: str,
    existing_rag_id: Optional[str] = None,
    force_recreate: bool = False
) -> str:
    """
    Создает RAG коллекцию для презентации или добавляет в существующую.
    
    Args:
        presentation_id: ID презентации
        file_path: Путь к файлу
        file_type: Тип файла
        existing_rag_id: ID существующей коллекции для добавления документов.
        force_recreate: Пересоздать коллекцию если существует (игнорируется если existing_rag_id задан).
        
    Returns:
        RAG ID (название коллекции в Qdrant)
    """
    
    # Загружаем документ
    documents = await load_document_from_file(file_path, file_type)
    
    # Разбиваем на чанки используя умный splitter
    text_splitter = get_text_splitter()
    splits = text_splitter.split_documents(documents)
    
    # Добавляем метаданные
    for split in splits:
        split.metadata["presentation_id"] = presentation_id
        split.metadata["source_file"] = Path(file_path).name
    
    # Создаем embeddings
    embeddings = get_embeddings()
    
    # Создаем Qdrant клиент
    qdrant_client = get_qdrant_client()

    if existing_rag_id:
        collection_name = existing_rag_id
        # Проверяем, существует ли коллекция
        try:
            qdrant_client.get_collection(collection_name=collection_name)
        except Exception:
            # Если не существует, создаем ее заново
             existing_rag_id = None # Сбрасываем, чтобы создать ниже
    
    if not existing_rag_id:
        # Генерируем уникальное имя коллекции
        collection_name = f"{COLLECTION_PREFIX}_{presentation_id}_{uuid.uuid4().hex[:8]}"
        
        # Удаляем старую коллекцию если force_recreate=True
        if force_recreate:
            # Удаляем все коллекции для этой презентации
            collections = qdrant_client.get_collections().collections
            for collection in collections:
                if collection.name.startswith(f"{COLLECTION_PREFIX}_{presentation_id}_"):
                    try:
                        qdrant_client.delete_collection(collection.name)
                    except Exception:
                        pass
        
        # Создаем новую коллекцию
        try:
            embedding_dimension = EMBEDDING_DIMENSIONS.get(EMBEDDING_MODEL, 1536)
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dimension,
                    distance=Distance.COSINE
                )
            )
        except Exception as e: 
            # Проверяем, может коллекция уже существует
            try:
                qdrant_client.get_collection(collection_name=collection_name)
            except Exception:
                 raise ValueError(f"Collection creation failed and it does not exist: {e}")

    # Создаем векторное хранилище и добавляем документы
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    
    # Добавляем документы в коллекцию
    vector_store.add_documents(splits)
    
    return collection_name


async def search_context(
    rag_id: str,
    query: str,
    top_k: int = 5
) -> str:
    """
    Ищет релевантный контекст в RAG коллекции
    
    Args:
        rag_id: ID RAG коллекции
        query: Поисковый запрос
        top_k: Количество результатов
        
    Returns:
        Объединенный контекст из найденных документов
    """
    embeddings = get_embeddings()
    qdrant_client = get_qdrant_client()
    
    # Создаем векторное хранилище
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=rag_id,
        embedding=embeddings,
    )
    
    # Используем similarity_search из LangChain
    results = vector_store.similarity_search(query, k=top_k)
    
    # Объединяем результаты
    context = "\n\n---\n\n".join([doc.page_content for doc in results])
    
    return context


async def get_full_context(rag_id: str, max_chunks: int = 20) -> str:
    """
    Получает весь контекст из RAG коллекции
    
    Args:
        rag_id: ID RAG коллекции
        max_chunks: Максимальное количество чанков
        
    Returns:
        Объединенный контекст
    """
    try:
        qdrant_client = get_qdrant_client()
        embeddings = get_embeddings()
        
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=rag_id,
            embedding=embeddings,
        )
        
        # Получаем все документы (или первые max_chunks)
        # Используем dummy query для получения документов
        results = vector_store.similarity_search("overview summary", k=max_chunks)
        
        context = "\n\n".join([doc.page_content for doc in results])
        return context
    except Exception as e:
        return f"Error retrieving context: {e}"


async def delete_rag_collection(rag_id: str) -> bool:
    """
    Удаляет RAG коллекцию
    
    Args:
        rag_id: ID RAG коллекции
        
    Returns:
        True если успешно удалено
    """
    try:
        qdrant_client = get_qdrant_client()
        qdrant_client.delete_collection(collection_name=rag_id)
        return True
    except Exception:
        return False
