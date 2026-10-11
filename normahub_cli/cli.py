"""
Command Line Interface for NormaHub Engine & Local Gateway.
"""

import argparse
import os
import sys
import webbrowser

from .cache import LocalCacheManager
from .models_data import MODELS_CATALOG
from .patcher import IDEPatcher
from .server import NormaHubGatewayServer


def cmd_start(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("NORMAHUB_API_KEY", "")
    server = NormaHubGatewayServer(port=args.port, api_key=api_key)

    if args.open_browser:
        def open_ui():
            import time
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
    print("\n[+] Total 30 models connected. Direct access from Russia without VPN.\n")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    cache = LocalCacheManager()
    stats = cache.get_stats()
    print("\n================= NORMAHUB FINOPS & CACHE METRICS =================")
    print(f" Total Gateway Requests: {stats['total_requests']}")
    print(f" Local Cache Hits:       {stats['cache_hits']} ({stats['hit_rate_pct']}%)")
    print(f" Total Tokens Saved:     {stats['tokens_saved']}")
    print(f" Money Saved for Team:   {stats['rubles_saved']} ₽")
    print(f" Cached Prompt Entries:  {stats['total_cached_entries']}")
    print("===================================================================\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="normahub",
        description="NormaHub Universal AI Gateway, Local Engine & Model Arena."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Command: start
    p_start = subparsers.add_parser("start", help="Start the local AI gateway daemon & Web UI")
    p_start.add_argument("-p", "--port", type=int, default=8000, help="Gateway HTTP port (default: 8000)")
    p_start.add_argument("--api-key", help="NormaHub API key (or set NORMAHUB_API_KEY)")
    p_start.add_argument("--open-browser", action="store_true", help="Automatically open Model Arena Web UI in browser")

    # Command: setup
    p_setup = subparsers.add_parser("setup", help="Auto-configure Cursor, Cline, OpenCode, Claude Desktop")
    p_setup.add_argument("--ide", default="all", choices=["cursor", "cline", "opencode", "claude", "all"], help="Target IDE")
    p_setup.add_argument("-p", "--port", type=int, default=8000, help="Local gateway port (default: 8000)")
    p_setup.add_argument("--api-key", help="NormaHub API key")

    # Command: models
    subparsers.add_parser("models", help="List all 30 connected models with prices and tiers")

    # Command: stats
    subparsers.add_parser("stats", help="Display local cache hits and money saved (RUB)")

    args = parser.parse_args()

    if args.subcommand == "start":
        return cmd_start(args)
    elif args.subcommand == "setup":
        return cmd_setup(args)
    elif args.subcommand == "models":
        return cmd_models(args)
    elif args.subcommand == "stats":
        return cmd_stats(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
