from app.services.hybrid_search_service import hybrid_search

test_queries = [
    "Spring Security configuration",
    "UserDetailsService implementation",
    "Journal entry CRUD operations", 
    "MongoDB configuration in Spring",
    "REST API endpoints for journal"
]

print("\nTesting Confidence Scores with Better Queries:")
print("=" * 80)

for query in test_queries:
    results = hybrid_search(7, query, top_k=3)
    if results:
        top_sim = results[0].get("similarity", 0)
        status = "✅ PASS" if top_sim >= 0.35 else "❌ FAIL"
        print(f"\n{status} Query: '{query}'")
        print(f"    Top similarity: {top_sim:.4f} (threshold: 0.35)")
        print(f"    Would generate answer: {'Yes' if top_sim >= 0.35 else 'No (blocked by confidence gate)'}")
    else:
        print(f"\n❌ FAIL Query: '{query}' - No results")

print("\n" + "=" * 80)
