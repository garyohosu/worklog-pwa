"""Tests for lib/cors.py — TC-SEC-CORS."""
import pytest
from lib.cors import is_allowed_origin, cors_headers, ALLOWED_ORIGINS


# TC-SEC-CORS-01
def test_github_pages_allowed():
    assert is_allowed_origin("https://garyohosu.github.io") is True


# TC-SEC-CORS-02
def test_localhost_allowed():
    assert is_allowed_origin("http://localhost") is True


# TC-SEC-CORS-03
def test_localhost_with_port_allowed():
    assert is_allowed_origin("http://localhost:3000") is True
    assert is_allowed_origin("http://localhost:5500") is True


def test_127_0_0_1_allowed():
    assert is_allowed_origin("http://127.0.0.1") is True


def test_127_0_0_1_with_port_allowed():
    assert is_allowed_origin("http://127.0.0.1:8080") is True


# TC-SEC-CORS-04
def test_evil_origin_blocked():
    assert is_allowed_origin("https://evil.example.com") is False
    assert is_allowed_origin("https://garyohosu.github.io.evil.com") is False


# TC-SEC-CORS-05
def test_empty_origin_blocked():
    assert is_allowed_origin("") is False
    assert is_allowed_origin(None) is False


def test_cors_headers_contain_origin():
    headers = cors_headers("https://garyohosu.github.io")
    joined = "\n".join(headers)
    assert "https://garyohosu.github.io" in joined
    assert "Access-Control-Allow-Origin" in joined
    assert "Access-Control-Allow-Methods" in joined
