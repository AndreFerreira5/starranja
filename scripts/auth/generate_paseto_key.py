#!/usr/bin/env python3
"""
Generates a cryptographically secure 32-byte key

Usage:
    python scripts/generate_paseto_key.py
    python scripts/generate_paseto_key.py --format env
    python scripts/generate_paseto_key.py --multiple 5
"""

import argparse
import secrets
import sys
from pathlib import Path


def generate_key() -> str:
    """
    Generate a cryptographically secure 32-byte key.

    Returns:
        str: 64-character hexadecimal string
    """
    return secrets.token_hex(32)


def validate_key(key: str) -> bool:
    """
    Validate a PASETO key format.

    Args:
        key: The key to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if len(key) != 64:
        return False
    try:
        bytes.fromhex(key)
        return True
    except ValueError:
        return False


def print_key_plain(key: str) -> None:
    """Print key in plain format."""
    print(key)


def print_key_env_format(key: str) -> None:
    """Print key in .env file format."""
    print("# Add this line to your .env file:")
    print(f"PASETO_SECRET_KEY={key}")


def print_key_with_instructions(key: str) -> None:
    """Print key with detailed instructions."""
    print("=" * 80)
    print("PASETO v4.local Symmetric Key Generated")
    print("=" * 80)
    print()
    print("Your new PASETO secret key:")
    print(f"  {key}")
    print()
    print("Key Details:")
    print(f"  • Length: {len(key)} characters (64 hex chars = 32 bytes)")
    print("  • Format: Hexadecimal")
    print("  • Algorithm: PASETO v4.local (XChaCha20-Poly1305)")
    print()
    print("Next Steps:")
    print("  1. Copy the key above")
    print("  2. Add it to your .env file:")
    print(f"     PASETO_SECRET_KEY={key}")
    print("  3. NEVER commit this key to version control")
    print("  4. Use different keys for dev/staging/production")
    print()
    print("Security Reminders:")
    print("  • Store production keys in a secure vault")
    print("  • Rotate keys periodically")
    print("  • Changing the key invalidates all existing tokens")
    print("  • Keep backups of your keys in secure storage")
    print()
    print("=" * 80)


def main() -> None:
    """Main entry point for the key generation utility."""
    parser = argparse.ArgumentParser(
        description="Generate secure PASETO v4.local symmetric keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a single key with instructions
  python generate_paseto_key.py

  # Generate key in .env format
  python generate_paseto_key.py --format env

  # Generate key only (for scripting)
  python generate_paseto_key.py --format plain

  # Generate multiple keys at once
  python generate_paseto_key.py --multiple 3

  # Validate an existing key
  python generate_paseto_key.py --validate YOUR_KEY_HERE
        """,
    )

    parser.add_argument(
        "--format",
        choices=["plain", "env", "detailed"],
        default="detailed",
        help="Output format (default: detailed)",
    )

    parser.add_argument(
        "--multiple",
        type=int,
        metavar="N",
        help="Generate N keys at once",
    )

    parser.add_argument(
        "--validate",
        metavar="KEY",
        help="Validate an existing key instead of generating",
    )

    parser.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        help="Write key to file instead of stdout",
    )

    args = parser.parse_args()

    # Validation mode
    if args.validate:
        is_valid = validate_key(args.validate)
        if is_valid:
            print("Valid PASETO key format")
            print(f"  Length: {len(args.validate)} characters")
            print("  Format: Valid hexadecimal")
            sys.exit(0)
        else:
            print("Invalid PASETO key format", file=sys.stderr)
            print("  Key must be exactly 64 hexadecimal characters", file=sys.stderr)
            sys.exit(1)

    # Multiple keys mode
    if args.multiple:
        if args.multiple < 1:
            print("Error: --multiple must be at least 1", file=sys.stderr)
            sys.exit(1)

        print(f"Generating {args.multiple} PASETO keys:")
        print("=" * 80)
        for i in range(args.multiple):
            key = generate_key()
            print(f"Key {i + 1}: {key}")
        print("=" * 80)
        sys.exit(0)

    # Single key generation
    key = generate_key()

    # Output to file if specified
    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(key)
            print(f"Key written to: {args.output}")
            sys.exit(0)
        except OSError as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)

    # Output to stdout based on format
    if args.format == "plain":
        print_key_plain(key)
    elif args.format == "env":
        print_key_env_format(key)
    else:
        print_key_with_instructions(key)


if __name__ == "__main__":
    main()
