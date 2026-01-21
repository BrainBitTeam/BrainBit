#!/usr/bin/env python3
"""
AI Chat CLI entry point.

Run with: python -m ai_chat [options]
"""

import argparse
import sys
from typing import NoReturn

from .chat import RadioChat
from .config import ChatConfig, LLMProviderType


BANNER = """
╔═══════════════════════════════════════════════════════════╗
║              Radio Control AI Chat                        ║
║                                                           ║
║  Commands: 'help' - show capabilities                     ║
║            'reset' - clear conversation history           ║
║            'quit' or 'exit' - exit chat                   ║
╚═══════════════════════════════════════════════════════════╝
"""


def print_help():
    """Print help information about available commands."""
    print("""
Available capabilities:

QUERY (ask about):
  - frequency, bandwidth, modulation, waveform
  - power, channel, volume
  - battery, members, errors, status
  - config (all settings), BIT (diagnostics)
  - GPS, LED, receive-only mode status

CONTROL (modify):
  - frequency: set to value or change by delta (MHz)
  - bandwidth: 25/50 kHz (NB) or 0.5/1/2/4 MHz (WB)
  - modulation: 8PSK/QAM16 (NB) or QAM4/16/32/64 (WB)
  - waveform: WB (wideband) or NB (narrowband)
  - power: low/medium/high
  - channel: 1-200
  - volume: 1-10
  - GPS, LED, receive-only: on/off
  - BIT: perform diagnostics

Example questions:
  "What's the current frequency?"
  "Show me the battery status"
  "How many members are connected?"
  "What are all the settings?"

Example commands:
  "Set frequency to 450 MHz"
  "Change volume to 8"
  "Turn on GPS"
  "Switch to narrowband"
  "Perform BIT"
""")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Interactive AI chat for radio control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--simulate", "-s",
        action="store_true",
        help="Run in simulation mode (no real radio connection)",
    )
    parser.add_argument(
        "--claude", "-c",
        action="store_true",
        help="Use Claude API instead of Ollama (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--host",
        default="192.168.1.11",
        help="Radio target IP address (default: 192.168.1.11)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Radio target port (default: 5000)",
    )
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Ollama model to use (default: llama3.2:3b)",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Disable confirmation for control commands",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> ChatConfig:
    """Build configuration from command line arguments."""
    from .config import NetworkConfig, OllamaConfig, ConversationConfig

    provider = LLMProviderType.CLAUDE if args.claude else LLMProviderType.OLLAMA

    return ChatConfig(
        provider=provider,
        simulation_mode=args.simulate,
        network=NetworkConfig(
            host=args.host,
            port=args.port,
        ),
        ollama=OllamaConfig(
            model=args.model,
        ),
        conversation=ConversationConfig(
            require_confirmation_for_control=not args.no_confirm,
        ),
    )


def run_chat(chat: RadioChat) -> NoReturn:
    """Run the interactive chat loop."""
    print(BANNER)

    success, message = chat.initialize()
    if not success:
        print(f"Initialization failed: {message}")
        sys.exit(1)

    print(f"Status: {message}")
    if chat.is_simulation:
        print("Note: Running in SIMULATION mode - no real radio connected")
    print("\nType 'help' for available commands, 'quit' to exit.\n")

    try:
        while True:
            try:
                if chat.awaiting_confirmation:
                    prompt = "[y/n] > "
                else:
                    prompt = "You: "

                user_input = input(prompt).strip()

                # Handle meta commands
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                if user_input.lower() == "help":
                    print_help()
                    continue

                if user_input.lower() == "reset":
                    chat.reset()
                    print("Conversation history cleared.")
                    continue

                if not user_input:
                    continue

                # Process input
                result = chat.process_input(user_input)
                print(f"Radio: {result.response}")
                print()

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
                if chat.awaiting_confirmation:
                    # Cancel pending command on Ctrl+C
                    chat.reset()
                    print("Pending command cancelled.")
                continue

    finally:
        chat.shutdown()

    sys.exit(0)


def main():
    """Main entry point."""
    args = parse_args()
    config = build_config(args)
    chat = RadioChat(config)
    run_chat(chat)


if __name__ == "__main__":
    main()
