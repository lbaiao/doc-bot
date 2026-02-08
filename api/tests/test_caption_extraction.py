import pytest
from unittest.mock import MagicMock, patch
import pymupdf
from preprocessing.pdf_extraction import PdfExtractor, UsedAreaTracker

class MockRect(pymupdf.Rect):
    def __init__(self, x0, y0, x1, y1):
        super().__init__(x0, y0, x1, y1)

@pytest.fixture
def tracker():
    return UsedAreaTracker()

@pytest.fixture
def extractor():
    # Mock init to avoid file operations
    with patch("preprocessing.pdf_extraction.PdfExtractor.__init__", return_value=None):
        ext = PdfExtractor("dummy.pdf")
        return ext

def test_used_area_tracker_overlap(tracker):
    rect1 = pymupdf.Rect(0, 0, 100, 100)
    tracker.mark_used(rect1)
    
    # Significant overlap
    rect2 = pymupdf.Rect(10, 10, 90, 90)
    assert tracker.is_used(rect2) is True
    
    # No overlap
    rect3 = pymupdf.Rect(200, 200, 300, 300)
    assert tracker.is_used(rect3) is False
    
    # Tiny overlap (below threshold)
    rect4 = pymupdf.Rect(99, 99, 200, 200)
    assert tracker.is_used(rect4, threshold=0.1) is False

def test_extract_caption_duplicate_prevention(extractor, tracker):
    page = MagicMock()
    
    # Layout:
    # Image 1: (0, 0, 100, 100)
    # Caption: (0, 110, 100, 130) "Figure 1: Test"
    # Image 2: (0, 140, 100, 240)
    
    img1_rect = pymupdf.Rect(0, 0, 100, 100)
    caption_rect = pymupdf.Rect(0, 110, 100, 130)
    img2_rect = pymupdf.Rect(0, 140, 100, 240)
    
    # Mock blocks: (x0, y0, x1, y1, text, block_no, block_type)
    blocks = [
        (0, 110, 100, 130, "Figure 1: Test Caption", 0, 0)
    ]
    page.get_text.return_value = blocks
    
    # First image should get the caption
    has_cap, text = extractor.extract_image_caption(page, img1_rect, tracker)
    assert has_cap is True
    assert text == "Figure 1: Test Caption"
    assert tracker.is_used(caption_rect) is True
    
    # Second image should NOT get the caption (it's used)
    has_cap2, text2 = extractor.extract_image_caption(page, img2_rect, tracker)
    assert has_cap2 is False
    assert text2 == ""

def test_extract_caption_keyword_priority(extractor, tracker):
    page = MagicMock()
    
    # Layout:
    # Image: (0, 0, 100, 100)
    # Text A (closer, no keyword): (0, 105, 100, 115) "Some body text"
    # Text B (further, keyword): (0, 120, 100, 140) "Figure 1: Real Caption"
    
    img_rect = pymupdf.Rect(0, 0, 100, 100)
    
    blocks = [
        (0, 105, 100, 115, "Some body text", 0, 0),
        (0, 120, 100, 140, "Figure 1: Real Caption", 1, 0)
    ]
    page.get_text.return_value = blocks
    
    has_cap, text = extractor.extract_image_caption(page, img_rect, tracker)
    
    # Expect keyword text to win despite being slightly further
    assert has_cap is True
    assert text == "Figure 1: Real Caption"

def test_extract_caption_distance_priority(extractor, tracker):
    page = MagicMock()
    
    # Layout:
    # Image: (0, 0, 100, 100)
    # Caption A (closer): (0, 110, 100, 120) "Figure 1"
    # Caption B (further): (0, 200, 100, 210) "Figure 2"
    
    img_rect = pymupdf.Rect(0, 0, 100, 100)
    
    blocks = [
        (0, 110, 100, 120, "Figure 1", 0, 0),
        (0, 200, 100, 210, "Figure 2", 1, 0)
    ]
    page.get_text.return_value = blocks
    
    has_cap, text = extractor.extract_image_caption(page, img_rect, tracker)
    
    assert has_cap is True
    assert text == "Figure 1"
