from typing import List, Optional, Dict, Any
from app.schemas.chat_schemas import ChatMessage # For type hinting chat_history
import structlog
import json # For formatting external_data if it's a dict/list

logger = structlog.get_logger(__name__)

# Placeholder for expert summaries - In a real app, this might come from a config file or DB
DEFAULT_EXPERT_SUMMARIES = {
    '交易醫生': '專注於短線交易策略，例如跳空SOP1（針對逆勢情況下的缺口封閉策略）和跳空SOP2（在誘騙行為發生後，順應趨勢進行追擊的策略），這些都是非常具體的盤中即時操作技巧。',
    '刀疤老二': '推崇趨勢交易的核心理念，強調「順勢而為」，主張在市場回檔時買入，採用「金字塔式加碼」策略來管理倉位，並且嚴格控制每一筆交易的「風險報酬比」。',
    'Comemail': '奉行逆向價值投資哲學，核心思想是「買冷賣熱」。致力於發掘市場上被忽略的「冷門股」，以及由特定事件驅動的交易機會（例如公司下市、合併收購等）。',
    'Vincent余鄭文': '運用一套完整的基本面分析框架。他以ROIC（投入資本回報率）作為衡量公司品質的核心指標，同時評估市場的潛在規模（TAM），並警惕那些可能導致「劣質增長」的因素。他也提倡一種從股價反向推導市場預期的逆向思維方法。'
}


def build_initial_analysis_prompt(
    shan_jia_lang_post: str,
    date_range: str, # Example: "2023-10-01至2023-10-07" or "2023年第40週"
    expert_summaries: Optional[Dict[str, str]] = None,
    external_data: Optional[Dict[str, Any]] = None,
    selected_modules: Optional[List[str]] = None
) -> str:
    logger.info('Building initial analysis prompt.', date_range=date_range, selected_modules=selected_modules)

    active_expert_summaries = expert_summaries if expert_summaries is not None else DEFAULT_EXPERT_SUMMARIES.copy()

    # If selected_modules are provided, filter the summaries to include only those selected experts.
    if selected_modules:
        filtered_summaries = {name: summary for name, summary in active_expert_summaries.items() if name in selected_modules}
        if not filtered_summaries and active_expert_summaries: # If selection results in empty, maybe log a warning or use all
            logger.warn("Selected modules resulted in no expert summaries. Using all available summaries.", requested_modules=selected_modules)
        elif filtered_summaries:
             active_expert_summaries = filtered_summaries
        # If selected_modules is empty list, it implies no specific experts, so use all.

    expert_block = "\n".join([f'- 「{name}」: {summary}' for name, summary in active_expert_summaries.items()])
    if not expert_block: # Handle case where no experts are selected or available
        expert_block = "    [未指定或無可用專家策略參考]"

    external_data_block = "\n            [無外部經濟數據參考]" # Default if no data
    if external_data:
        try:
            # Attempt to pretty-print JSON, ensure_ascii=False for CJK characters
            external_data_json = json.dumps(external_data, indent=2, ensure_ascii=False)
            external_data_block = f'''
3.  **外部經濟數據參考:**
    ```json
    {external_data_json}
    ```'''
        except Exception:
            logger.warn('Failed to serialize external_data for prompt, using raw string.', exc_info=True)
            external_data_block = f'''
3.  **外部經濟數據參考:**
    ```
    {str(external_data)}
    ```
    [注意：以上數據格式化失敗，可能影響AI判讀]'''


    prompt = f'''任務指令：金融市場分析週報撰寫 (初稿)

作為一位頂尖的金融市場分析師，請根據以下提供的多元背景資料，針對「{date_range}」這段期間，撰寫一份專業、深入、結構化的週報分析初稿。請使用**繁體中文**，並以條理清晰、層次分明的 **Markdown** 格式進行輸出。

**核心背景資料:**

1.  **當週核心分析對象「善甲狼」的原文:**
    ```text
    {shan_jia_lang_post}
    ```

2.  **輔助分析框架與專家策略參考:**
    你將運用以下幾位市場專家的核心交易理念來豐富你的分析維度：
{expert_block}
{external_data_block}

**報告結構要求：**

請**嚴格按照**以下五個部分結構，生成報告內容。每一部分的標題和子標題都必須清晰呈現。

**A. 週次與日期範圍:**
    *   [請直接填寫當週的具體日期範圍，例如：{date_range}]

**B. 「善甲狼」核心觀點摘要:**
    *   精確提煉「善甲狼」在當週貼文中的核心觀點、市場情緒、關鍵的買賣決策或持倉變化。
    *   深入分析其操作背後的主要邏輯和判斷依據。

**C. 當週市場重點回顧:**
    *   基於「善甲狼」貼文內容、**您獲得的外部經濟數據**以及您自身的金融知識庫，全面回顧並總結當週全球及台灣市場的宏觀經濟動態與重大金融事件。
    *   簡述主要市場指數（例如：S&P 500、NASDAQ、道瓊工業指數、台股加權指數、櫃買指數等）的整體表現及其關鍵驅動因素。

**D. 當週其他市場觀點/大師風向探索 (深入對比分析):**
    *   請進行一次有深度的對比分析。將「善甲狼」當週的市場行為和觀點，與我們提供的其他專家理念（見「輔助分析框架」部分）進行比較。
    *   **具體操作指引：**
        *   思考「善甲狼」的決策，在何種程度上呼應或偏離了其他專家的策略？
        *   例如：若「善甲狼」在市場急跌時進行了某項操作，這更接近「刀疤老二」所提倡的「順勢回檔」機會，還是「Comemail」視角下的「錯殺冷門股」的佈局良機？
        *   若「善甲狼」看好某特定產業或股票，嘗試運用「Vincent余鄭文」的ROIC及TAM等基本面分析標準來初步檢視，這是否構成一個具吸引力的投資機會？
    *   請清晰闡述您的判斷邏輯和理由。

**E. 「看到->想到->做到」框架下的潛在交易機會回顧:**
    *   **看到 (Observation):** 綜合以上所有資訊（「善甲狼」觀點、市場動態、專家策略、外部數據），條列出當週市場最值得關注的幾個關鍵現象、訊號、數據點或潛在預期差。
    *   **想到 (Analysis/Hypothesis):** 針對您「看到」的每一個現象，進行策略性思考和深度分析。請務必融合**至少兩位以上**提供的專家分析角度，來形成具體的交易假設或市場判斷。
    *   **做到 (Actionable Plan):** 將上述交易假設轉化為具體的、可回顧的「紙上談兵」交易計畫。內容應包含：
        *   明確的進場條件或觀察訊號。
        *   假設性的初始停損點設定。
        *   初步的資金管理考量（例如，為何這是個值得投入注意力的機會）。
        *   這個部分是回顧性質，旨在提煉和學習，而非實際交易指令。

請確保報告內容的專業性和洞察力，充分利用所提供的所有上下文信息。
'''
    logger.debug("Initial analysis prompt built.", prompt_length=len(prompt))
    return prompt

def build_final_report_preview_prompt(sections: Dict[str, str]) -> str:
    logger.info('Building final report preview prompt.')

    # Ensure all sections A-E are present, use placeholder if not.
    section_content_a = sections.get('A', '[A節內容未提供]')
    section_content_b = sections.get('B', '[B節內容未提供]')
    section_content_c = sections.get('C', '[C節內容未提供]')
    section_content_d = sections.get('D', '[D節內容未提供]')
    section_content_e = sections.get('E', '[E節內容未提供]')

    prompt = f'''任務指令：彙整金融週報最終稿

你是一位專業的排版助理。你的任務是將我提供給你的五個獨立的、已經過最終確認的章節文本，嚴格按照A、B、C、D、E的順序，彙整成一份單一的、格式工整、閱讀流暢的 Markdown 報告。

**核心要求：**
*   **絕對不要修改、刪減、增加或總結任何章節的文字內容。** 你的唯一職責就是將這些文本塊按照指定順序和格式無縫地拼接在一起。
*   確保最終輸出的報告保持原始 Markdown 格式，包括標題層級（例如 `##` 或 `###`）、列表、粗體、引言等。
*   如果某個章節的內容未提供（顯示為 "[X節內容未提供]"），請在最終報告中如實保留該提示。

**待彙整的章節內容如下：**

**A. 週次與日期範圍:**
{section_content_a}

**B. 「善甲狼」核心觀點摘要:**
{section_content_b}

**C. 當週市場重點回顧:**
{section_content_c}

**D. 當週其他市場觀點/大師風向探索:**
{section_content_d}

**E. 「看到->想到->做到」框架下的潛在交易機會回顧:**
{section_content_e}

請立即開始彙整工作，並直接輸出完整的 Markdown 報告。
'''
    logger.debug("Final report preview prompt built.", prompt_length=len(prompt))
    return prompt

# Note: For interactive refinement (general chat), the AI service (Gemini) handles history.
# The role of this service is primarily to construct the initial, complex prompts for specific tasks.
# If a "system prompt" or initial instruction is needed for general chat, it can be added here
# or managed by the AI service when initiating a chat session.

def build_system_prompt_for_chat() -> Optional[str]:
    """
    Optional: Builds a system prompt that can be used to set the AI's persona or provide general instructions
    at the beginning of a conversation or when no specific trigger_action is provided.
    For Gemini, this might be sent as the first part of the user's initial message or through specific API configurations if available.
    """
    # Example system prompt (can be much more detailed)
    # system_prompt = "你是一位樂於助人且知識淵博的AI助理，專長於金融市場分析。請以繁體中文回答問題。"
    # logger.debug("Built system prompt for chat.")
    # return system_prompt
    return None # Returning None if no explicit system prompt is desired for every interaction by default.

# Example of how to prepare history for Gemini, if needed here (though likely in ai_service.py)
# def prepare_history_for_gemini(chat_history: List[ChatMessage]) -> List[Dict[str, Any]]:
#     gemini_history = []
#     for msg in chat_history:
#         role = 'user' if msg.role == 'user' else 'model' # Convert 'assistant'/'system' if necessary
#         gemini_history.append({'role': role, 'parts': [{'text': msg.content}]})
#     return gemini_history
