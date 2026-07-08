"""
AI News Summarization Module.

This module leverages Google Gemini models to provide concise, technical 
summaries of AI news items in Vietnamese. It includes logic for batch 
processing, token management, and structured formatting.
"""

from typing import List, Dict
from src.agent.model_rotator import generate_content
from src.utils.text_utils import normalize_text

def summarize_news(news_list: List[Dict], keywords: str, known_models: List[str]) -> List[Dict]:
    """
    Translates and summarizes technical news into Vietnamese.
    
    Args:
        news_list: List of raw news dictionaries (title, link, summary, source).
        keywords: Current trending keywords for context.
        known_models: List of AI models for priority highlighting.
        
    Returns:
        List of dictionaries with Vietnamese summaries.
    """
    if not news_list:
        return []

    summaries = []

    # --- Block: Batching Strategy ---
    # To minimize API roundtrips, we combine multiple news items into a single
    # prompt. We process in chunks of 5 items to stay within token limits 
    # and maintain summarization quality.
    chunk_size = 5
    for i in range(0, len(news_list), chunk_size):
        chunk = news_list[i : i + chunk_size]
        
        # --- Block: Prompt Construction ---
        # The prompt is designed to ensure technical accuracy while translating 
        # to Vietnamese. We enforce a HARD CONSTRAINT to always output Vietnamese.
        prompt = f"""
Bạn là một chuyên gia nghiên cứu AI. Hãy tóm tắt danh sách tin tức AI dưới đây sang tiếng Việt.

CẢNH BÁO QUAN TRỌNG (HARD CONSTRAINT): 
- Mọi kết quả tóm tắt PHẢI bằng tiếng Việt (Vietnamese). 
- KHÔNG ĐƯỢC giữ nguyên các ngôn ngữ khác ngoài tiếng Việt (trừ các thuật ngữ kỹ thuật tiếng Anh).
- Nếu nội dung gốc là tiếng Trung, tiếng Nhật hoặc ngôn ngữ khác, hãy DỊCH các ý chính sang tiếng Việt.

YÊU CẦU:
1. Độ dài: tóm tắt ngắn gọn (3-4 câu).
2. Ngôn ngữ: Tiếng Việt chuyên ngành công nghệ. Giữ nguyên các thuật ngữ tiếng Anh quan trọng (ví dụ: 'Transformer', 'Fine-tuning', 'Agentic', 'Orchestration').
3. Ưu tiên:
   - Nếu là tin về ỨNG DỤNG (Applied AI) hoặc AGENT: Hãy giải thích RÕ cách nó hoạt động và lợi ích/giá trị thực tế (Business Value).
   - Nếu là tin về MODEL: Nêu bật các thông số kỹ thuật hoặc khả năng mới so với bản cũ.
4. Định dạng: Trả về chính xác cấu trúc bên dưới cho từng item.
5. Ngữ cảnh: Tập trung vào {keywords} hoặc các model: {', '.join(known_models[:10])}.

TIN TỨC CẦN TÓM TẮT:
"""
        for idx, item in enumerate(chunk):
            prompt += f"\nITEM_{idx}:\nTiêu đề: {item.get('title')}\nNguồn: {item.get('source')}\nNội dung gốc: {item.get('summary')}\n---\n"

        prompt += "\nOUTPUT FORMAT (TRẢ VỀ EXACTLY DƯỚI ĐÂY):\n"
        for idx in range(len(chunk)):
            prompt += f"ITEM_{idx}_VN: [Tóm tắt tiếng Việt]\n"

        # --- Block: Generation & Error Handling ---
        try:
            response = generate_content(prompt)

            # --- Block: Response Parsing ---
            # Extract the Vietnamese summaries from the raw model response.
            for idx, item in enumerate(chunk):
                marker = f"ITEM_{idx}_VN:"
                if marker in response:
                    # Extract content between this marker and the next one (or end of string).
                    start_idx = response.find(marker) + len(marker)
                    next_marker = f"ITEM_{idx+1}_VN:"

                    if next_marker in response:
                        summary_vn = response[start_idx : response.find(next_marker)].strip()
                    else:
                        summary_vn = response[start_idx:].strip()
                        
                    summaries.append({
                        "title": item.get('title'),
                        "link": item.get('link'),
                        "source": item.get('source', 'Unknown'),
                        "summary_vn": summary_vn,
                        "date": item.get('date')
                    })
        except Exception as e:
            # If AI generation fails (e.g. safety filters, context length),
            # we log the error and skip this chunk to allow the pipeline to proceed.
            print(f"  Warning: Summarization failed for chunk starting at {i}: {e}")
            
    return summaries
