import base64
import logging
import io
from typing import List, Literal, Optional
import pymupdf
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class SmartFigure(BaseModel):
    """Structured extraction of a figure/table from a page."""
    label: str = Field(description="The figure label, e.g., 'Figure 1' or 'Table 2'")
    caption: str = Field(description="The full caption text found on the page for this figure")
    description: str = Field(description="A brief visual description of the figure content")
    bbox_2d: List[int] = Field(description="Approximate bounding box [x0, y0, x1, y1] in PDF coordinates (0-1000 scale, where 0,0 is top-left)")
    type: Literal["figure", "table", "chart", "diagram"]

class PageExtractionResult(BaseModel):
    """Container for all figures found on a page."""
    figures: List[SmartFigure]

class SmartPageExtractor:
    """
    Uses Vision LLM (Claude) to analyze a PDF page and extract structured figure data.
    """
    def __init__(self, model_name: str = "claude-3-5-sonnet-latest"):
        self.llm = ChatAnthropic(
            model=model_name,
            temperature=0,
            max_tokens=4096
        )
        self.structured_llm = self.llm.with_structured_output(PageExtractionResult)

    def extract_from_page(self, page: pymupdf.Page) -> PageExtractionResult:
        """
        Render page to image and send to Claude for analysis.
        """
        # 1. Render page to high-res image
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        
        # 2. Construct prompt
        system_prompt = (
            "You are an expert document layout analyzer. "
            "Your task is to identify all figures, tables, charts, and diagrams on this page. "
            "For each item, extract its EXACT caption text as it appears on the page. "
            "Also provide a brief visual description and an approximate bounding box "
            "using a 0-1000 scale (where 0,0 is top-left and 1000,1000 is bottom-right)."
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": "Extract all figures and tables from this page."
                }
            ])
        ]
        
        # 3. Call LLM
        logger.info(f"Sending page {page.number + 1} to Vision LLM...")
        try:
            result = self.structured_llm.invoke(messages)
            logger.info(f"Extracted {len(result.figures)} items from page {page.number + 1}")
            return result
        except Exception as e:
            logger.error(f"Failed to extract figures with Vision LLM: {e}")
            raise
