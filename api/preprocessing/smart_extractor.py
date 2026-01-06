import base64
import logging
import io
from typing import List, Literal, Optional
import pymupdf
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class SmartFigure(BaseModel):
    """Structured extraction of a figure/table from a page."""
    label: str = Field(description="The figure label, e.g., 'Figure 1' or 'Table 2'")
    caption: str = Field(description="The full caption text found on the page for this figure")
    description: str = Field(description="A brief visual description of the figure content")
    bbox_2d: List[int] = Field(description="Approximate bounding box [x0, y0, x1, y1] of the visual graphic ONLY (excluding caption text) in PDF coordinates (0-1000 scale, where 0,0 is top-left)")
    type: Literal["figure", "table", "chart", "diagram"]

class PageExtractionResult(BaseModel):
    """Container for all figures found on a page."""
    figures: List[SmartFigure]

class SmartPageExtractor:
    """
    Uses Vision LLM (Claude) to analyze a PDF page and extract structured figure data.
    """
    def __init__(self, model_name: str = "claude-3-5-sonnet-latest", api_key: Optional[str] = None):
        self.llm = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=0,
            max_tokens=4096
        )
        self.structured_llm = self.llm.with_structured_output(PageExtractionResult)

    def _apply_visual_grid(self, img: Image.Image) -> Image.Image:
        """
        Overlay a 0-1000 coordinate grid on the image to help the LLM with spatial reasoning.
        """
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Draw grid lines every 100 units
        for i in range(0, 1001, 100):
            # Vertical lines
            x = (i / 1000.0) * width
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
            
            # Horizontal lines
            y = (i / 1000.0) * height
            draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
            
            # Labels
            try:
                # Try to use a default font, fallback to basic if needed
                font = ImageFont.load_default()
            except Exception:
                font = None
                
            draw.text((x + 2, 2), str(i), fill=(150, 0, 0), font=font)
            draw.text((2, y + 2), str(i), fill=(150, 0, 0), font=font)
            
        return img

    def extract_from_page(self, page: pymupdf.Page) -> PageExtractionResult:
        """
        Render page to image, apply visual grid, and send to Claude for analysis.
        """
        # 1. Render page to high-res image
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # 2. Apply Visual Grid
        img_with_grid = self._apply_visual_grid(img)
        
        # Convert back to base64
        buffered = io.BytesIO()
        img_with_grid.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # 3. Construct prompt
        system_prompt = (
            "You are an expert document layout analyzer. "
            "Your task is to identify all figures, tables, charts, and diagrams on this page. "
            "The image has a coordinate grid overlaid (0-1000 scale). "
            "Use these grid lines and labels to determine exact bounding boxes. "
            "For each item, extract its EXACT caption text as it appears on the page. "
            "Also provide a brief visual description and an approximate bounding box "
            "[x0, y0, x1, y1] using the 0-1000 scale. "
            "IMPORTANT: The bounding box should cover ONLY the visual element (the graphic/table/chart) "
            "and MUST EXCLUDE the caption text itself."
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
                    "text": "Extract all figures and tables from this page using the coordinate grid for accuracy."
                }
            ])
        ]
        
        # 4. Call LLM
        logger.info(f"Sending page {page.number + 1} with Visual Grid to Vision LLM...")
        try:
            result = self.structured_llm.invoke(messages)
            logger.info(f"Extracted {len(result.figures)} items from page {page.number + 1}")
            return result
        except Exception as e:
            logger.error(f"Failed to extract figures with Vision LLM: {e}")
            raise
