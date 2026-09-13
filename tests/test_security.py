import pytest
from thai_legal_mcp.security import assert_allowed_url

def test_allowed():
    assert_allowed_url("https://www.ocs.go.th/searchlaw-law")
    assert_allowed_url("https://deka.supremecourt.or.th/")

def test_blocked():
    with pytest.raises(ValueError):
        assert_allowed_url("https://example.com/")
