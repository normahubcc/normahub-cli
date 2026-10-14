"""
Command Line Interface for NormaHub Engine & Local Gateway.
"""

import argparse
import json
import os
import sys
import time
import webbrowser

from .cache import LocalCacheManager
from .client import NormaHubUpstreamClient
from .models_data import MODELS_CATALOG
from .patcher import IDEPatcher
from .server import NormaHubGatewayServer


def cmd_start(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "")
    server = NormaHubGatewayServer(port=args.port, api_key=api_key)

    if args.open_browser:
        def open_ui():
            time.sleep(0.5)
            webbrowser.open(f"http://localhost:{args.port}/ui")
        import threading
        threading.Thread(target=open_ui, daemon=True).start()

    server.start()
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "nr_hub_local")
    ide = args.ide.lower()

    print(f"[*] Configuring IDE integrations for NormaHub (Port: {args.port})...\n")

    if ide == "all":
        results = IDEPatcher.patch_all(api_key, args.port)
        for name, ok, msg in results:
            prefix = "[+]" if ok else "[-]"
            print(f"{prefix} {name:<15}: {msg}")
    elif ide == "cursor":
        ok, msg = IDEPatcher.patch_cursor(api_key, args.port)
        print(f"{'[+]' if ok else '[-]'} Cursor: {msg}")
    elif ide == "cline":
        ok, msg = IDEPatcher.patch_cline(api_key, args.port)
        print(f"{'[+]' if ok else '[-]'} Cline: {msg}")
    elif ide == "opencode":
        ok, msg = IDEPatcher.patch_opencode(api_key, args.port)
        print(f"{'[+]' if ok else '[-]'} OpenCode: {msg}")
    elif ide == "claude":
        ok, msg = IDEPatcher.patch_claude_desktop(api_key, args.port)
        print(f"{'[+]' if ok else '[-]'} Claude Desktop: {msg}")
    else:
        print(f"[!] Unknown IDE: {ide}. Supported: cursor, cline, opencode, claude, all")
        return 1

    print("\n[✔] Setup complete! Restart your IDE to apply the configuration.")
    return 0


def cmd_models(_args: argparse.Namespace) -> int:
    print(f"\n{'ID':<25} | {'VENDOR':<12} | {'IN / 1M':<10} | {'OUT / 1M':<10} | {'TIER'}")
    print("-" * 75)
    for m in MODELS_CATALOG:
        in_p = f"${m['input_price_1m']:.4f}" if m['input_price_1m'] > 0 else "Free / Fix"
        out_p = f"${m['output_price_1m']:.4f}" if m['output_price_1m'] > 0 else "-"
        print(f"{m['id']:<25} | {m['vendor']:<12} | {in_p:<10} | {out_p:<10} | {m['tier']}")
    print(f"\nTotal models: {len(MODELS_CATALOG)}\n")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    cache = LocalCacheManager()
    stats = cache.get_stats()
    print("\n--- Cache and FinOps Metrics ---")
    print(f"Total Requests:       {stats['total_requests']}")
    print(f"Cache Hits:           {stats['cache_hits']} ({stats['hit_rate_pct']}%)")
    print(f"Tokens Saved:         {stats['tokens_saved']}")
    print(f"Cost Saved (RUB):     {stats['rubles_saved']} ₽")
    print(f"Cached Entries:       {stats['total_cached_entries']}")
    print("--------------------------------\n")
    return 0


def cmd_ping(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "")
    client = NormaHubUpstreamClient(api_key=api_key)

    print("\n[🔍] Pinging NormaHub Cloud Gateway...")
    ping_res = client.check_ping()
    balance_res = client.get_balance() if api_key else {"balance": None}

    print("--------------------------------------------------")
    print(f"Target URL:    {ping_res.get('base_url')}")
    status = ping_res.get("status")
    if status == "connected":
        print(f"Status:        ONLINE ({ping_res.get('latency_ms')} ms)")
        print(f"Active Models: {ping_res.get('models_count')}")
    else:
        print(f"Status:        {status}")
        if "error" in ping_res:
            print(f"Error:         {ping_res.get('error')}")

    if api_key:
        masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"API Key:       {masked_key}")
        bal = balance_res.get("balance")
        curr = balance_res.get("currency", "RUB")
        if bal is not None:
            print(f"Balance:       {bal:.2f} {curr}")
        else:
            print("Balance:       [Active Account / Custom Rate]")
    else:
        print("API Key:       Not configured (NORMAHUB_API_KEY is unset)")
    print("--------------------------------------------------\n")
    return 0 if ping_res.get("status") == "connected" else 1


def cmd_ask(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "")
    prompt = args.prompt

    # Support stdin piping: cat log.txt | normahub ask "find errors"
    if not prompt or prompt == "-":
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            print("[!] Error: No prompt provided. Usage: normahub ask 'Your question'")
            return 1

    if not prompt:
        print("[!] Error: Empty prompt received.")
        return 1

    model = args.model or "deepseek-v4.1-flash"
    client = NormaHubUpstreamClient(api_key=api_key)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    try:
        buffer = ""
        for chunk_bytes in client.stream_chat(payload):
            chunk_str = chunk_bytes.decode("utf-8", errors="ignore")
            buffer += chunk_str
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                for line in event.splitlines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            if "error" in data_json:
                                print(f"\n[!] Error from API: {data_json['error']}")
                                return 1
                            choices = data_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    sys.stdout.write(content)
                                    sys.stdout.flush()
                        except Exception:
                            pass
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0
    except Exception as e:
        print(f"\n[!] Request failed: {e}")
        return 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "")
    if not api_key:
        print("[!] Error: API key required for benchmark. Provide --api-key or set NORMAHUB_API_KEY.")
        return 1

    models = args.models.split(",") if args.models else [
        "deepseek-v4.1-flash",
        "claude-sonnet-5-5",
        "gpt-6-astra",
        "llama-3.3-70b",
    ]
    models = [m.strip() for m in models if m.strip()]

    prompt = args.prompt or "Write a python function to compute fibonacci numbers with memoization. Explain briefly."
    client = NormaHubUpstreamClient(api_key=api_key)

    print(f"\n🚀 Running NormaHub Multi-Model Benchmark ({len(models)} models)")
    print(f"📝 Prompt: \"{prompt[:60]}...\"\n")
    print(f"{'MODEL':<24} | {'TTFT':<10} | {'TOK/S':<10} | {'TOTAL (s)':<10} | {'STATUS'}")
    print("-" * 72)

    for m in models:
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 120,
        }
        start_time = time.perf_counter()
        ttft = None
        token_count = 0
        error_msg = None

        try:
            buffer = ""
            for chunk_bytes in client.stream_chat(payload):
                chunk_str = chunk_bytes.decode("utf-8", errors="ignore")
                buffer += chunk_str
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    for line in event.splitlines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data_json = json.loads(data_str)
                                if "error" in data_json:
                                    error_msg = data_json["error"].get("message", "Error")
                                    break
                                choices = data_json.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content", "")
                                    if content:
                                        if ttft is None:
                                            ttft = (time.perf_counter() - start_time) * 1000.0
                                        token_count += 1
                            except Exception:
                                pass
                if error_msg:
                    break

            total_time = time.perf_counter() - start_time
            if error_msg:
                print(f"{m:<24} | {'-':<10} | {'-':<10} | {total_time:<10.2f} | ✖ {error_msg[:18]}")
            else:
                ttft_str = f"{ttft:.1f} ms" if ttft is not None else "N/A"
                speed = f"{(token_count / total_time):.1f}" if total_time > 0 and token_count > 0 else "N/A"
                print(f"{m:<24} | {ttft_str:<10} | {speed:<10} | {total_time:<10.2f} | ✔ OK ({token_count} tok)")
        except Exception as e:
            total_time = time.perf_counter() - start_time
            print(f"{m:<24} | {'-':<10} | {'-':<10} | {total_time:<10.2f} | ✖ {str(e)[:18]}")

    print("-" * 72)
    print("Benchmark completed.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="normahub",
        description="Локальный AI Gateway демон и CLI для NormaHub API."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Доступные команды")

    # Command: start
    p_start = subparsers.add_parser("start", help="Запустить локальный gateway-сервер и Web UI")
    p_start.add_argument("-p", "--port", type=int, default=8000, help="Порт HTTP сервера (по умолчанию: 8000)")
    p_start.add_argument("--api-key", help="API-ключ NormaHub (или переменная NORMAHUB_API_KEY)")
    p_start.add_argument("--open-browser", action="store_true", help="Автоматически открыть Web UI в браузере")

    # Command: setup
    p_setup = subparsers.add_parser("setup", help="Авто-настройка окружения для Cursor, Cline, OpenCode, Claude")
    p_setup.add_argument("--ide", default="all", choices=["cursor", "cline", "opencode", "claude", "all"], help="Целевая среда разработки")
    p_setup.add_argument("-p", "--port", type=int, default=8000, help="Порт локального шлюза (по умолчанию: 8000)")
    p_setup.add_argument("--api-key", help="API-ключ NormaHub")

    # Command: models
    subparsers.add_parser("models", help="Вывести каталог поддерживаемых моделей и тарифы")

    # Command: stats
    subparsers.add_parser("stats", help="Показать статистику кэша и сэкономленные средства (₽)")

    # Command: ping
    p_ping = subparsers.add_parser("ping", help="Проверить сетевой статус, RTT задержку и баланс")
    p_ping.add_argument("--api-key", help="API-ключ NormaHub")

    # Command: ask
    p_ask = subparsers.add_parser("ask", help="Быстрый однострочный вопрос в LLM со стримингом ответа")
    p_ask.add_argument("prompt", nargs="?", default="", help="Текст запроса (или ввод через пайплайн)")
    p_ask.add_argument("-m", "--model", default="deepseek-v4.1-flash", help="Модель (по умолчанию: deepseek-v4.1-flash)")
    p_ask.add_argument("--api-key", help="API-ключ NormaHub")

    # Command: benchmark
    p_bench = subparsers.add_parser("benchmark", help="Замерить TTFT, токены/сек и задержку по моделям")
    p_bench.add_argument("-m", "--models", help="Список моделей через запятую")
    p_bench.add_argument("-p", "--prompt", help="Кастомный промпт для теста")
    p_bench.add_argument("--api-key", help="API-ключ NormaHub")

    args = parser.parse_args()

    if args.subcommand == "start":
        return cmd_start(args)
    elif args.subcommand == "setup":
        return cmd_setup(args)
    elif args.subcommand == "models":
        return cmd_models(args)
    elif args.subcommand == "stats":
        return cmd_stats(args)
    elif args.subcommand == "ping":
        return cmd_ping(args)
    elif args.subcommand == "ask":
        return cmd_ask(args)
    elif args.subcommand == "benchmark":
        return cmd_benchmark(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
