from app.services.hybrid_search_service import hybrid_search

results = hybrid_search(7, "what architecture is used", top_k=3)
print("\\nHybrid Search Results:")
print("=" * 60)
for i, r in enumerate(results, 1):
    sim = r.get("similarity", 0)
    score = r.get("score", 0)
    print(f"{i}. Similarity: {sim:.4f}, Score: {score:.4f}")
    print(f"   Content preview: {r['content'][:80]}...")
print("=" * 60)

# Check if confidence gate would pass
top_sim = results[0].get("similarity", 0) if results else 0
print(f"\\nTop confidence: {top_sim:.4f}")
print(f"Threshold: 0.35")
print(f"Would pass gate: {'✅ YES' if top_sim >= 0.35 else '❌ NO'}")
