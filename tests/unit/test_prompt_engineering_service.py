import pytest
from app.services.prompt_engineering_service import (
    build_initial_analysis_prompt,
    build_final_report_preview_prompt,
    DEFAULT_EXPERT_SUMMARIES # Import to check against default behavior
)
import json # For checking JSON formatting in prompt

# Minimal valid inputs for initial analysis prompt
MINIMAL_POST = "善甲狼本週貼文。"
MINIMAL_DATE_RANGE = "2023-W01"

def test_build_initial_analysis_prompt_basic_structure():
    """Tests the basic structure and inclusion of key elements."""
    prompt = build_initial_analysis_prompt(shan_jia_lang_post=MINIMAL_POST, date_range=MINIMAL_DATE_RANGE)

    assert f"為「{MINIMAL_DATE_RANGE}」這段期間" in prompt
    assert MINIMAL_POST in prompt

    # Check for all default expert summaries inclusion
    for expert_name, summary in DEFAULT_EXPERT_SUMMARIES.items():
        assert f"「{expert_name}」" in prompt
        assert summary in prompt

    # Check for all five main sections A, B, C, D, E
    assert "A. 週次與日期範圍:" in prompt
    assert "B. 「善甲狼」核心觀點摘要:" in prompt
    assert "C. 當週市場重點回顧:" in prompt
    assert "D. 當週其他市場觀點/大師風向探索 (深入對比分析):" in prompt
    assert "E. 「看到->想到->做到」框架下的潛在交易機會回顧:" in prompt

    # Ensure no external data block if not provided
    assert "外部經濟數據參考:" not in prompt # Original check was fine
    assert "[無外部經濟數據參考]" in prompt # Check for the placeholder text

def test_build_initial_analysis_prompt_with_external_data():
    """Tests inclusion and formatting of external data."""
    ext_data = {"CPI": "3.0%", "InterestRate": "5.0%"}
    prompt = build_initial_analysis_prompt(
        shan_jia_lang_post=MINIMAL_POST,
        date_range=MINIMAL_DATE_RANGE,
        external_data=ext_data
    )

    assert "外部經濟數據參考:" in prompt
    # Check if the JSON dump is present and correctly formatted (indent=2, ensure_ascii=False for Chinese)
    expected_json_dump = json.dumps(ext_data, indent=2, ensure_ascii=False)
    assert expected_json_dump in prompt

def test_build_initial_analysis_prompt_with_selected_modules():
    """Tests filtering of expert summaries based on selected_modules."""
    selected = ["交易醫生", "Comemail"] # Select two specific experts
    # Provide a custom expert_summaries dict to ensure filtering logic is tested against it
    custom_experts = {
        "交易醫生": "交易醫生策略。",
        "刀疤老二": "刀疤老二策略。",
        "Comemail": "Comemail策略。"
    }
    prompt = build_initial_analysis_prompt(
        shan_jia_lang_post=MINIMAL_POST,
        date_range=MINIMAL_DATE_RANGE,
        selected_modules=selected,
        expert_summaries=custom_experts # Pass the custom dict
    )

    assert custom_experts["交易醫生"] in prompt
    assert custom_experts["Comemail"] in prompt
    assert custom_experts["刀疤老二"] not in prompt # This expert was not selected

def test_build_initial_analysis_prompt_selected_modules_empty_uses_all_provided():
    """Tests that if selected_modules is empty, all provided experts are used."""
    custom_experts = {"ExpertA": "SummaryA", "ExpertB": "SummaryB"}
    prompt = build_initial_analysis_prompt(
        shan_jia_lang_post=MINIMAL_POST,
        date_range=MINIMAL_DATE_RANGE,
        selected_modules=[], # Empty list
        expert_summaries=custom_experts
    )
    assert custom_experts["ExpertA"] in prompt
    assert custom_experts["ExpertB"] in prompt

def test_build_initial_analysis_prompt_no_selected_modules_uses_defaults_or_provided():
    """Tests that if selected_modules is None, default/provided experts are used."""
    # Test with default experts
    prompt_default = build_initial_analysis_prompt(
        shan_jia_lang_post=MINIMAL_POST, date_range=MINIMAL_DATE_RANGE, selected_modules=None
    )
    for summary in DEFAULT_EXPERT_SUMMARIES.values():
        assert summary in prompt_default

    # Test with custom experts when selected_modules is None
    custom_experts = {"OnlyExpert": "OnlySummary"}
    prompt_custom = build_initial_analysis_prompt(
        shan_jia_lang_post=MINIMAL_POST, date_range=MINIMAL_DATE_RANGE, selected_modules=None, expert_summaries=custom_experts
    )
    assert custom_experts["OnlyExpert"] in prompt_custom


def test_build_final_report_preview_prompt_all_sections():
    """Tests formatting with all sections provided."""
    sections = {
        "A": "Content for Section A.",
        "B": "Content for Section B.",
        "C": "Content for Section C.",
        "D": "Content for Section D.",
        "E": "Content for Section E.",
    }
    prompt = build_final_report_preview_prompt(sections)

    for key, value in sections.items():
        assert f"{key.upper()}. " in prompt # Check for section headers like "A. "
        assert value in prompt
    assert "絕對不要修改、刪減、增加或總結任何章節的文字內容" in prompt

def test_build_final_report_preview_prompt_missing_sections():
    """Tests that placeholders are used for missing sections."""
    sections = {"A": "Only content for A.", "D": "Only content for D."}
    prompt = build_final_report_preview_prompt(sections)

    assert sections["A"] in prompt
    assert "[B節內容未提供]" in prompt
    assert "[C節內容未提供]" in prompt
    assert sections["D"] in prompt
    assert "[E節內容未提供]" in prompt
