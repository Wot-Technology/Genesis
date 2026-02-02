#!/usr/bin/env python3
"""
Seed a pool with content from text.

Usage:
    python seed_pool.py --pool "stained-glass" --file content.txt
    python seed_pool.py --pool "stained-glass" --text "Some content here"
    python seed_pool.py --pool "stained-glass" --generate  # Use built-in stained glass content
"""

import argparse
import sys
from pathlib import Path
from typing import List

import core
import pool as pool_mgmt

# Thread-2 RAG for indexing
THREAD2_DIR = Path(__file__).parent.parent / "thread-2"
sys.path.insert(0, str(THREAD2_DIR))


STAINED_GLASS_CONTENT = """
## Lead Came vs Copper Foil

Lead came is the traditional method for assembling stained glass panels. H-shaped lead channels hold glass pieces together. The came is measured in heart size (internal channel width) - typically 3/16" to 1/2". Wider came creates bolder lines but reduces light transmission.

Copper foil (Tiffany method) uses thin copper tape wrapped around each glass edge, then soldered together. This allows for finer detail and curved lines impossible with lead. The foil must overlap consistently - usually 1/16" on each side.

## Glass Types

Cathedral glass is transparent, machine-made, with uniform color. Good for backgrounds and large areas where light transmission matters.

Opalescent glass contains mineral compounds that make it partially opaque. Colors appear different in reflected vs transmitted light. Louis Comfort Tiffany pioneered its use for shading and depth.

Streaky glass combines cathedral and opalescent in swirled patterns. Each piece is unique. Cutting requires careful planning to use the patterns effectively.

Flashed glass has a thin color layer fused to a clear or lighter base. You can sandblast or acid-etch through the flash layer to create two-tone effects.

## Cutting Techniques

Score once, firmly, with consistent pressure. Never go over the same line twice - this chips the glass. The score weakens the glass along the molecular structure.

Running pliers apply even pressure on both sides of the score to propagate the break. Position them perpendicular to the score line, centered on the glass edge.

Grozing pliers nibble away small amounts for curves. Work from multiple directions to avoid stress fractures. Keep cuts perpendicular to the edge.

For inside curves, make relief cuts first - straight scores from the curve to the glass edge. Break out the waste pieces, then work the curve.

## Soldering

60/40 solder (60% tin, 40% lead) melts at 374°F. It's the standard for copper foil work. Flows smoothly, creates rounded beads.

50/50 solder melts at 421°F. Preferred for lead came because higher temp won't melt the lead. Creates flatter seams.

Flux removes oxidation so solder bonds to metal. Oleic acid flux for copper foil, tallow-based for lead. Apply sparingly - excess causes pitting.

Iron temperature matters. Too cool = solder won't flow. Too hot = burns flux, melts lead, creates cold joints. Around 700°F for copper foil, 650°F for lead.

## Patina and Finishing

Copper patina turns solder lines copper-brown. Apply to clean, flux-free solder. Neutralize with baking soda solution after.

Black patina creates dark antiqued look. Works on both copper foil and lead. Multiple coats deepen the color.

Cement (putty) fills gaps between lead came and glass. Traditional mix: whiting powder, linseed oil, lampblack. Work under the came with a fid, clean excess with sawdust.

Wax polish protects lead from oxidation. Beeswax-based works best. Apply after cementing cures (24-48 hours).

## Design Principles

Lead lines are structural - they must support the panel's weight. Design so lead creates a continuous matrix. Avoid isolated glass islands.

T-joints are stronger than Y-joints. Four-way intersections are weak points - offset them into two T-joints.

Glass expands with heat. Large panels need flexible mounting to prevent cracking. Outdoor installations require steel reinforcement bars.

Color temperature affects perception. Warm colors (red, orange, yellow) advance. Cool colors (blue, green, violet) recede. Use this for depth.

Grain direction in textured glass affects light. Horizontal grain creates calm, vertical creates energy. Radial grain draws the eye inward.
"""


def chunk_content(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks, respecting paragraph boundaries."""
    paragraphs = text.strip().split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = len(para)

        if current_size + para_size > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def seed_pool(pool_name: str, content: str, identity: core.Identity):
    """Create pool and seed with chunked content."""

    # Find or create pool
    pools = pool_mgmt.list_pools()
    pool = None
    for p in pools:
        if p.name.lower() == pool_name.lower():
            pool = p
            break

    if not pool:
        pool = pool_mgmt.create_pool(
            name=pool_name,
            identity=identity,
            rules=pool_mgmt.PoolRules(
                waterline=0.3,
                require_because=False,
                accept_schemas=["basic", "insight", "knowledge", "message"],
            ),
            visibility="private",
            description=f"Content pool: {pool_name}"
        )
        print(f"Created pool: {pool.name} ({pool.cid[:30]}...)")
    else:
        print(f"Using existing pool: {pool.name} ({pool.cid[:30]}...)")

    # Chunk and store content
    chunks = chunk_content(content)
    print(f"Storing {len(chunks)} thoughts...")

    stored = []
    for i, chunk in enumerate(chunks):
        # Extract title from markdown header if present
        title = None
        if chunk.startswith('##'):
            first_line = chunk.split('\n')[0]
            title = first_line.replace('##', '').strip()

        thought = core.create_thought(
            content={
                "text": chunk,
                "title": title,
                "chunk_index": i,
            },
            thought_type="knowledge",
            identity=identity,
            because=[pool.cid] if i == 0 else [pool.cid, stored[-1].cid],
            visibility=f"pool:{pool.cid}",
            source=f"seed/{pool_name}"
        )
        core.store_thought(thought)
        stored.append(thought)
        print(f"  [{i+1}/{len(chunks)}] {thought.cid[:30]}... {title or chunk[:40]}...")

    # Index in RAG
    try:
        from wellspring_embeddings import WellspringRAG
        rag = WellspringRAG(
            thought_db_path=core.DB_PATH,
            vec_db_path=Path(__file__).parent / "wellspring_vec.db"
        )
        print(f"\nIndexing {len(stored)} thoughts in RAG...")
        for t in stored:
            rag.pipeline.embed_thought(t, pool.cid)
        print("Done!")
        rag.close()
    except ImportError as e:
        print(f"\nRAG not available: {e}")
        print("Run: pip install sentence-transformers numpy")

    return pool, stored


def main():
    parser = argparse.ArgumentParser(description="Seed a pool with content")
    parser.add_argument('--pool', '-p', required=True, help="Pool name")
    parser.add_argument('--file', '-f', help="Read content from file")
    parser.add_argument('--text', '-t', help="Content text directly")
    parser.add_argument('--generate', '-g', action='store_true',
                        help="Use built-in stained glass content")

    args = parser.parse_args()

    # Load identity
    identity_path = Path(__file__).parent / "daemon-identity.json"
    if identity_path.exists():
        identity = core.load_identity(identity_path)
    else:
        identity = core.create_identity("seed-user")
        core.save_identity(identity, identity_path)

    # Get content
    if args.generate:
        content = STAINED_GLASS_CONTENT
    elif args.file:
        content = Path(args.file).read_text()
    elif args.text:
        content = args.text
    else:
        print("Error: provide --file, --text, or --generate")
        sys.exit(1)

    pool, thoughts = seed_pool(args.pool, content, identity)
    print(f"\nPool '{pool.name}' now has {len(thoughts)} new thoughts")
    print(f"CID: {pool.cid}")


if __name__ == "__main__":
    main()
