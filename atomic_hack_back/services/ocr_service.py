import base64
import io
import os
import asyncio
import logging
from typing import Optional
from pathlib import Path

import fitz  # pymupdf - кроссплатформенная замена pdf2image
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import httpx

logger = logging.getLogger("app.ocr")

# Environment configuration
QWEN_VL_API_BASE = os.getenv("QWEN_VL_API_BASE", "https://api.openai.com/v1")
QWEN_VL_API_KEY = os.getenv("QWEN_VL_API_KEY", "")
QWEN_VL_MODEL_NAME = os.getenv("QWEN_VL_MODEL_NAME", "Qwen/Qwen-VL-Max")
ENABLE_OCR = os.getenv("ENABLE_OCR", "false").lower() in ("true", "1", "yes")
GOTENBERG_API_URL = os.getenv("GOTENBERG_URL", "http://localhost:3000")


def get_vl_llm_client() -> ChatOpenAI:
    """Creates a client for the Vision-Language Model (Qwen-VL)."""
    if not QWEN_VL_API_KEY:
        raise RuntimeError("QWEN_VL_API_KEY environment variable is not set.")
    return ChatOpenAI(
        base_url=QWEN_VL_API_BASE,
        api_key=QWEN_VL_API_KEY,
        model=QWEN_VL_MODEL_NAME,
        temperature=0,
    )


def is_ocr_enabled() -> bool:
    """Check if OCR is enabled in configuration."""
    return ENABLE_OCR


async def _extract_text_from_image(image: Image.Image, page_num: int) -> str:
    """
    Extracts text from a single image using Qwen-VL model.
    
    Args:
        image: PIL Image object
        page_num: Page number (for logging)
        
    Returns:
        Extracted text from the image
    """
    # Convert image to base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Create the message for the vision model
    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": "Extract all text from this image. Preserve formatting and structure."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ]
        )
    ]

    # Invoke the model
    llm = get_vl_llm_client()
    response = await llm.ainvoke(messages)
    page_text = response.content
    
    logger.debug(f"OCR extracted {len(page_text)} characters from page {page_num}")
    return page_text


async def ocr_pdf_with_qwen_vl(file_path: str) -> str:
    """
    Performs OCR on a PDF file using Qwen-VL model.
    Uses PyMuPDF (fitz) for cross-platform PDF processing without external dependencies.

    Args:
        file_path: Path to the PDF file.

    Returns:
        The extracted text from the PDF.
    """
    if not is_ocr_enabled():
        raise RuntimeError("OCR is disabled in configuration (ENABLE_OCR=false)")
    
    logger.info(f"Starting OCR processing for PDF: {file_path}")
    
    try:
        # Convert PDF to images using PyMuPDF
        def convert_pdf_to_images(pdf_path: str):
            """Convert PDF pages to PIL Images using PyMuPDF"""
            doc = fitz.open(pdf_path)
            images = []
            for page_num, page in enumerate(doc):
                # Render page to an image (pixmap)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                images.append(img)
            doc.close()
            return images
        
        images = await asyncio.to_thread(convert_pdf_to_images, file_path)
        logger.info(f"PDF converted to {len(images)} images using PyMuPDF")

        all_text = ""

        for i, image in enumerate(images):
            try:
                page_text = await _extract_text_from_image(image, i + 1)
                all_text += f"\n\n--- Page {i+1} ---\n\n{page_text}"
            except Exception as e:
                logger.error(f"Error processing page {i+1}: {e}")
                all_text += f"\n\n--- Page {i+1} ---\n\n[Error processing page: {str(e)}]"

        logger.info(f"OCR completed. Total extracted: {len(all_text)} characters")
        return all_text.strip()
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise RuntimeError(f"Failed to process PDF: {e}")


async def ocr_image_with_qwen_vl(file_path: str) -> str:
    """
    Performs OCR on an image file using Qwen-VL model.

    Args:
        file_path: Path to the image file (PNG, JPG, etc.)

    Returns:
        The extracted text from the image.
    """
    if not is_ocr_enabled():
        raise RuntimeError("OCR is disabled in configuration (ENABLE_OCR=false)")
    
    logger.info(f"Starting OCR processing for image: {file_path}")
    
    # Open image
    image = await asyncio.to_thread(Image.open, file_path)
    
    page_text = await _extract_text_from_image(image, 1)
    
    logger.info(f"OCR completed. Total extracted: {len(page_text)} characters")
    return page_text


async def convert_document_to_pdf_with_gotenberg(file_path: str, file_type: str) -> str:
    """
    Converts a document (DOCX, DOC, PPTX, XLSX, etc.) to PDF using Gotenberg API.
    
    Args:
        file_path: Path to the document file
        file_type: Type of file (docx, doc, pptx, xlsx, etc.)
        
    Returns:
        Path to the temporary PDF file
        
    Raises:
        Exception: If conversion fails
    """
    logger.info(f"Converting {file_type} to PDF using Gotenberg API")
    
    import tempfile
    
    # Create temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Determine the correct Gotenberg endpoint based on file type
            if file_type in ["docx", "doc"]:
                endpoint = f"{GOTENBERG_API_URL}/forms/libreoffice/convert"
            elif file_type in ["pptx", "ppt"]:
                endpoint = f"{GOTENBERG_API_URL}/forms/libreoffice/convert"
            elif file_type in ["xlsx", "xls"]:
                endpoint = f"{GOTENBERG_API_URL}/forms/libreoffice/convert"
            else:
                endpoint = f"{GOTENBERG_API_URL}/forms/libreoffice/convert"
            
            # Upload file and convert to PDF
            with open(file_path, "rb") as f:
                files = {
                    "files": (Path(file_path).name, f, "application/octet-stream")
                }
                
                response = await client.post(
                    endpoint,
                    files=files,
                    data={"landscape": "false"},
                )
                
                if response.status_code != 200:
                    raise Exception(f"Gotenberg conversion failed: {response.status_code} - {response.text}")
                
                # Save the PDF
                with open(tmp_pdf_path, "wb") as pdf_file:
                    pdf_file.write(response.content)
                
                logger.info(f"Successfully converted {file_type} to PDF via Gotenberg")
                return tmp_pdf_path
    except Exception as e:
        logger.error(f"Gotenberg conversion failed: {e}")
        # Clean up temp file on error
        try:
            Path(tmp_pdf_path).unlink()
        except:
            pass
        raise


async def ocr_file_with_qwen_vl(file_path: str, file_type: str) -> Optional[str]:
    """
    Performs OCR on a file using Qwen-VL model.
    Supports PDF, image files, and Office documents (DOCX, DOC, PPTX, etc.)

    Args:
        file_path: Path to the file.
        file_type: Type of file (pdf, png, jpg, jpeg, docx, doc, pptx, etc.)

    Returns:
        The extracted text from the file, or None if OCR is not supported for this file type.
        
    Raises:
        RuntimeError: If OCR is disabled or other errors occur.
    """
    if not is_ocr_enabled():
        logger.debug("OCR is disabled, skipping")
        return None
    
    file_type = file_type.lower().lstrip('.')
    
    logger.info(f"Attempting OCR extraction for {file_type} file: {file_path}")
    
    try:
        if file_type == "pdf":
            return await ocr_pdf_with_qwen_vl(file_path)
        elif file_type in ["png", "jpg", "jpeg", "bmp", "gif", "webp"]:
            return await ocr_image_with_qwen_vl(file_path)
        elif file_type in ["docx", "doc", "pptx", "ppt", "xlsx", "xls"]:
            # For Office documents, convert to PDF using Gotenberg, then apply OCR
            logger.info(f"Converting {file_type} to PDF for OCR processing")
            
            tmp_pdf_path = None
            try:
                # Convert to PDF using Gotenberg
                tmp_pdf_path = await convert_document_to_pdf_with_gotenberg(file_path, file_type)
                
                # Now perform OCR on the generated PDF
                text = await ocr_pdf_with_qwen_vl(tmp_pdf_path)
                logger.info(f"OCR on converted PDF completed, extracted {len(text)} characters")
                return text
            finally:
                # Clean up temporary PDF
                if tmp_pdf_path:
                    try:
                        Path(tmp_pdf_path).unlink()
                        logger.debug(f"Cleaned up temporary PDF: {tmp_pdf_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete temporary PDF: {e}")
        else:
            logger.warning(f"OCR not supported for file type: {file_type}")
            return None
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise
