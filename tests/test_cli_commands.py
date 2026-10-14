"""Tests for new CLI commands: ping, ask, and benchmark."""

import argparse
from unittest.mock import MagicMock, patch

from normahub_cli.cli import cmd_ask, cmd_benchmark, cmd_ping


def test_cmd_ping_success(capsys):
    """Verify cmd_ping handles connected upstream gateway."""
    mock_client = MagicMock()
    mock_client.check_ping.return_value = {
        "status": "connected",
        "latency_ms": 42.5,
        "base_url": "https://api.normahub.cc/v1",
        "models_count": 28,
    }
    mock_client.get_balance.return_value = {
        "balance": 1500.0,
        "currency": "RUB",
    }

    with patch("normahub_cli.cli.NormaHubUpstreamClient", return_value=mock_client):
        args = argparse.Namespace(api_key="nr_live_test_key_1234567890")
        code = cmd_ping(args)
        assert code == 0

        captured = capsys.readouterr().out
        assert "ONLINE (42.5 ms)" in captured
        assert "Active Models: 28" in captured
        assert "1500.00 RUB" in captured


def test_cmd_ask_streaming(capsys):
    """Verify cmd_ask streams model response to stdout."""
    mock_client = MagicMock()
    # Mock SSE stream chunks
    mock_chunks = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        b'data: {"choices": [{"delta": {"content": " world!"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    mock_client.stream_chat.return_value = iter(mock_chunks)

    with patch("normahub_cli.cli.NormaHubUpstreamClient", return_value=mock_client):
        args = argparse.Namespace(
            prompt="Say hello",
            model="deepseek-v4.1-flash",
            api_key="test-key",
        )
        code = cmd_ask(args)
        assert code == 0

        captured = capsys.readouterr().out
        assert "Hello world!" in captured


def test_cmd_benchmark_run(capsys):
    """Verify cmd_benchmark computes metrics across selected models."""
    mock_client = MagicMock()
    mock_chunks = [
        b'data: {"choices": [{"delta": {"content": "Fibonacci "}}]}\n\n',
        b'data: {"choices": [{"delta": {"content": "solution"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    mock_client.stream_chat.return_value = iter(mock_chunks)

    with patch("normahub_cli.cli.NormaHubUpstreamClient", return_value=mock_client):
        args = argparse.Namespace(
            models="deepseek-v4.1-flash,claude-sonnet-5-5",
            prompt="Fib test",
            api_key="test-key",
        )
        code = cmd_benchmark(args)
        assert code == 0

        captured = capsys.readouterr().out
        assert "NormaHub Multi-Model Benchmark" in captured
        assert "deepseek-v4.1-flash" in captured
        assert "claude-sonnet-5-5" in captured
        assert "OK" in captured
