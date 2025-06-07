# services/prompt_builder.py
import logging
import pandas as pd
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

def build_gemini_request_contents(
    main_system_prompt: Optional[str],
    core_docs_contents: Optional[List[Dict[str, str]]], # Expecting [{'name': str, 'content': str}]
    external_data_summaries: Optional[Dict[str, Any]], # Expecting {'source_name': data}
    chat_history_for_prompt: Optional[List[Dict[str, Any]]], # Expecting chat history format
    current_user_input: str
) -> List[str]: # Returns a list of strings, to be passed to call_gemini_api's prompt_parts
    """
    Constructs the list of content parts for the Gemini API request.

    Args:
        main_system_prompt: The main system prompt/instruction.
        core_docs_contents: A list of dictionaries, each with 'name' and 'content' of a core document.
        external_data_summaries: A dictionary where keys are source names and values are data (e.g., DataFrames or strings).
        chat_history_for_prompt: The recent chat history to include.
        current_user_input: The latest user input/question.

    Returns:
        A list of strings, where each string is a part of the prompt to be sent to Gemini.
    """
    logger.info("PromptBuilder: Building Gemini request contents...")
    prompt_parts = []
    context_summary_log = [] # For logging what context was added

    # 1. Main System Prompt
    if main_system_prompt:
        prompt_parts.append(f"**主要指示 (System Prompt):**\n{main_system_prompt}")
        context_summary_log.append("系統提示詞")

    # 2. Core Documents Content
    if core_docs_contents:
        core_docs_text_parts = ["\n**核心分析文件內容 (Core Analysis Documents Content):**"]
        files_included_count = 0
        for doc in core_docs_contents:
            doc_name = doc.get("name", "未知文件")
            doc_content = doc.get("content", "")
            if isinstance(doc_content, str):
                core_docs_text_parts.append(f"--- Document Start: {doc_name} ---\n{doc_content}\n--- Document End: {doc_name} ---\n")
                files_included_count += 1
            elif isinstance(doc_content, pd.DataFrame):
                core_docs_text_parts.append(f"--- Document Start (Table): {doc_name} ---\n欄位: {', '.join(doc_content.columns)}\n數據 (前5行):\n{doc_content.head(5).to_string()}\n--- Document End (Table): {doc_name} ---\n")
                files_included_count += 1
            else: # bytes or other
                core_docs_text_parts.append(f"--- Document: {doc_name} (二進制或其他格式，長度: {len(doc_content) if hasattr(doc_content, '__len__') else 'N/A'}) ---\n")
                files_included_count += 1

        if files_included_count > 0:
            prompt_parts.append("\n".join(core_docs_text_parts))
            context_summary_log.append(f"{files_included_count}個核心文件")
        logger.debug(f"PromptBuilder: Added {files_included_count} core documents.")

    # 3. External Data Summaries
    if external_data_summaries:
        num_ext_sources = len(external_data_summaries)
        if num_ext_sources > 0:
            external_data_str = "\n**已引入的外部市場與總經數據摘要:**"
            for source, data_items in external_data_summaries.items():
                external_data_str += f"\n來源: {source.upper()}\n"
                if isinstance(data_items, dict): # e.g., yfinance returns a dict of DataFrames
                    for item_name, df_item in data_items.items():
                        if isinstance(df_item, pd.DataFrame):
                            external_data_str += f"  {item_name} (最近3筆):\n{df_item.tail(3).to_string(index=False)}\n"
                elif isinstance(data_items, pd.DataFrame): # e.g., FRED or NY Fed might return a single DataFrame
                     external_data_str += f"  {source}數據 (最近3筆):\n{data_items.tail(3).to_string(index=False)}\n"
            prompt_parts.append(external_data_str)
            context_summary_log.append(f"{num_ext_sources}個外部數據源")
        logger.debug(f"PromptBuilder: Added {num_ext_sources} external data sources.")

    # 4. Chat History (Simplified for now - this part might need more sophisticated role handling if Gemini expects structured chat)
    # The current `call_gemini_api` expects a list of strings which are joined.
    # For true chat history, `call_gemini_api` would need to be adapted to take `history` argument of `GenerativeModel.start_chat()`.
    # Here, we'll just append a summary or a few recent turns if needed.
    # However, the existing logic in chat_interface.py already sends the *current user input* as the last part.
    # The `full_prompt_parts` in `_trigger_gemini_response_processing` effectively *is* the entire context including history.
    # So, this builder might not need to explicitly handle chat_history separately if the caller passes it as part of other contexts.
    # For now, we assume `chat_history_for_prompt` is NOT the main st.session_state.chat_history, but a pre-formatted part.
    if chat_history_for_prompt:
        history_str_parts = ["\n**相關對話歷史 (Relevant Conversation History):**"]
        for msg in chat_history_for_prompt: # Assuming it's already filtered/summarized
            role = msg.get("role", "unknown")
            content = msg.get("parts", [""])[0] if msg.get("parts") else ""
            history_str_parts.append(f"{role.capitalize()}: {content}")
        if len(history_str_parts) > 1: # More than just the header
            prompt_parts.append("\n".join(history_str_parts))
            context_summary_log.append("相關對話歷史")
        logger.debug(f"PromptBuilder: Added {len(history_str_parts)-1} relevant history turns.")


    # 5. Current User Input (this should always be the last part for clarity to the model)
    prompt_parts.append(f"\n**使用者當前問題/指令:**\n{current_user_input}")
    context_summary_log.append("用戶當前問題")

    logger.info(f"PromptBuilder: Contents built. Context included: {', '.join(context_summary_log)}")
    final_prompt_str_for_logging = "\n---\n".join(prompt_parts)
    logger.debug(f"PromptBuilder: Final assembled prompt parts (joined for logging, total length {len(final_prompt_str_for_logging)}):\n{final_prompt_str_for_logging[:500]}...\n...{final_prompt_str_for_logging[-200:]}")

    return prompt_parts
