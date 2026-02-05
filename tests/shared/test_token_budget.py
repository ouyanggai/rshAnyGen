import pytest
from apps.shared.token_counter import TokenCounter

def test_token_budget_allocation():
    # Test qwen-max (30000 limit)
    counter = TokenCounter("qwen-max")
    budget = counter.get_token_budget(max_output_tokens=2000)
    
    # 30000 - 2000 - 100 = 27900
    expected_available = 27900
    assert budget["total"] == 30000
    assert budget["available_for_context"] == expected_available
    
    # 10% : 20% : 70%
    assert budget["long_term"] == int(expected_available * 0.1)
    assert budget["short_term"] == int(expected_available * 0.2)
    assert budget["working"] == int(expected_available * 0.7)

def test_token_budget_small_limit():
    # Test unknown model default (8192)
    counter = TokenCounter("unknown-model")
    budget = counter.get_token_budget(max_output_tokens=8000)
    
    # 8192 - 8000 - 100 = 92 < 1000
    # Should trigger fallback
    assert budget["long_term"] == 0
    assert budget["short_term"] == 0
    assert budget["working"] == 92
