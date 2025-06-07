import pytest
# The function check_for_search_intent is defined within app/routers/chat.py
# To test it directly in a unit test, it's best if it's easily importable.
# If it's a top-level function in chat.py, this import should work assuming PYTHONPATH is correct.
from app.routers.chat import check_for_search_intent

@pytest.mark.parametrize("message, expected_intent", [
    # Positive cases (should detect search intent)
    ("幫我查一下今天台北的天氣", True),
    ("查一下台積電的股價", True),
    ("搜尋AI的最新發展趨勢", True),
    ("搜索一部關於太空的電影", True),
    ("google一下蘋果公司的市值", True),
    ("what is the capital of France?", True),
    ("who is the current CEO of OpenAI?", True),
    ("search for python programming tutorials", True),
    ("find information on renewable energy sources", True),
    ("最新的iPhone型號是什麼？", True), # Contains '最新' and '什麼' + '?'
    ("現在比特幣的價格是多少？", True), # Contains '現在' and '多少' + '?'
    ("美國CPI數據是多少?", True), # Contains '多少' + '?'

    # Negative cases (should not detect search intent)
    ("這是一個普通的陳述句。", False),
    ("我今天感覺很好，謝謝。", False),
    ("明天會是個好天氣嗎？", True), # Question, but '天氣' is a keyword.
    ("你認為AI會取代人類嗎？", False), # Philosophical question, not direct info lookup by current keywords
    ("跟我說個笑話吧。", False),
    ("我的行程安排是什麼？", False), # Could be info seeking, but not matching current keywords for external search
    ("What do you think about this idea?", False), # Opinion seeking
    ("Explain the concept of recursion.", False) # Explanation, not necessarily real-time search
])
def test_check_for_search_intent(message: str, expected_intent: bool):
    """Tests the check_for_search_intent function with various messages."""
    assert check_for_search_intent(message) == expected_intent

def test_check_for_search_intent_empty_string():
    """Tests with an empty string."""
    assert check_for_search_intent("") == False

def test_check_for_search_intent_only_keywords():
    """Tests with messages that are only keywords."""
    assert check_for_search_intent("最新") == True
    assert check_for_search_intent("股價") == True # This might be too broad, depends on desired strictness
    assert check_for_search_intent("search for") == True # This might trigger if incomplete

def test_check_for_search_intent_case_insensitivity():
    """Tests case insensitivity of keywords."""
    assert check_for_search_intent("WHAT IS a transformer model?") == True
    assert check_for_search_intent("幫我查 APPLE INC.") == True

# Consider adding tests for messages that are questions but don't use keywords,
# if the logic for '?' + who/what/where/when/how is meant to be independent of keywords.
# The current implementation of check_for_search_intent combines keyword check OR (question mark + wh-word).
def test_check_for_search_intent_question_without_keywords():
    assert check_for_search_intent("這東西是什麼?") == True # "什麼" + "?"
    assert check_for_search_intent("他是誰啊?") == True # "誰" + "?"
    assert check_for_search_intent("我們在哪裡集合?") == True # "哪裡" + "?"
    assert check_for_search_intent("會議是何時開始?") == True # "何時" + "?"
    assert check_for_search_intent("How does this work?") == True # "how" + "?"
    assert check_for_search_intent("Why is the sky blue?") == False # "why" is not in current wh-list for questions, and no other keywords.
                                                                # This behavior is correct based on current implementation. Add 'why' if needed.
