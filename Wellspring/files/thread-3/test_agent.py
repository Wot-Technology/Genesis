#!/usr/bin/env python3
"""
Test script for the Wellspring Agent.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python test_agent.py

Or for a dry run (no API call):
    python test_agent.py --dry-run
"""

import os
import sys
from pathlib import Path

# Ensure we can import from this directory
sys.path.insert(0, str(Path(__file__).parent))

import wellspring_agent as agent
import core


def test_dry_run():
    """Test everything except the actual API call."""
    print("=== DRY RUN TEST ===\n")

    # 1. Create test identity
    print("1. Creating test identity...")
    identity = core.create_identity("test-agent")
    print(f"   CID: {identity.cid}")

    # 2. Create some context thoughts
    print("\n2. Creating context thoughts...")
    thoughts = [
        core.create_thought(
            content="WoT uses content-addressed thoughts connected by CIDs",
            thought_type="basic",
            identity=identity,
            source="test/context"
        ),
        core.create_thought(
            content={
                "category": "decision",
                "title": "Use SHA256 for CID computation",
                "body": "SHA256 provides good security and performance balance"
            },
            thought_type="trace",
            identity=identity,
            source="test/context"
        ),
    ]
    for t in thoughts:
        core.store_thought(t)
        print(f"   Stored: {t.cid[:40]}...")

    # 3. Test context assembly
    print("\n3. Testing context assembly...")
    context = agent.assemble_context(limit=10)
    print(f"   Context length: {len(context)} chars")
    print(f"   Preview: {context[:200]}...")

    # 4. Test response parsing
    print("\n4. Testing response parsing...")
    mock_response = '''
Based on the context, here are my thoughts:

<thought>
type: insight
content: The SHA256 choice for CID computation aligns with IPFS standards, making future integration straightforward.
because: cid:sha256:abc123
</thought>

<thought>
type: question
content: Should we support multiple hash algorithms for forward compatibility?
</thought>
'''
    parsed = agent.parse_llm_response(mock_response)
    print(f"   Parsed {len(parsed)} thoughts from mock response")
    for p in parsed:
        print(f"   - [{p['type']}] {p['content'][:60]}...")

    print("\n=== DRY RUN COMPLETE ===")
    print("All components working. Set ANTHROPIC_API_KEY to test full loop.")


def test_full_loop():
    """Test the complete agent loop with Claude API."""
    print("=== FULL LOOP TEST ===\n")

    # Create agent
    config = agent.AgentConfig(
        model="claude-sonnet-4-20250514",
        auto_store=True,
        source_prefix="test-agent"
    )
    wot_agent = agent.WellspringAgent(config)
    print(f"Agent identity: {wot_agent.identity.cid}")

    # Generate thoughts
    print("\nGenerating thoughts via Claude API...")
    user_input = """
    Review the context thoughts and generate:
    1. One insight about the WoT architecture
    2. One question that should be explored next

    Keep thoughts concise.
    """

    try:
        thoughts = wot_agent.generate(
            user_input=user_input,
            context_limit=10
        )

        print(f"\nGenerated {len(thoughts)} thoughts:")
        for t in thoughts:
            print(f"\n[{t.cid}]")
            print(f"  Type: {t.type}")
            print(f"  Content: {t.content}")
            if t.because:
                print(f"  Because: {t.because}")

        print("\n=== FULL LOOP COMPLETE ===")
        return True

    except Exception as e:
        print(f"\nError: {e}")
        return False


def main():
    if "--dry-run" in sys.argv:
        test_dry_run()
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY set. Running dry-run test.")
        print("To test with API: export ANTHROPIC_API_KEY=sk-ant-...\n")
        test_dry_run()
    else:
        test_full_loop()


if __name__ == "__main__":
    main()
