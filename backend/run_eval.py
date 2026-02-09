#!/usr/bin/env python
"""
RAG Evaluation Script

Supports Change → Measure → Iterate workflow:
1. Run baseline: python run_eval.py 7 --save baseline.json
2. Make changes to the system
3. Run again: python run_eval.py 7 --save after_change.json
4. Compare: python run_eval.py --compare baseline.json after_change.json

Usage:
    python run_eval.py <repo_id> [--save FILE] [--no-reranker] [--limit N]
    python run_eval.py --compare FILE1 FILE2
"""

import asyncio
import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def compare_results(file1: str, file2: str):
    """Compare two evaluation results for Change → Measure → Iterate workflow."""
    with open(file1) as f:
        r1 = json.load(f)
    with open(file2) as f:
        r2 = json.load(f)
    
    print("\n" + "=" * 70)
    print("📊 COMPARISON: Change → Measure → Iterate")
    print("=" * 70)
    print(f"Baseline: {file1}")
    print(f"After:    {file2}")
    print("=" * 70)
    
    def delta(v1, v2, is_pct=False):
        diff = v2 - v1
        sign = "+" if diff >= 0 else ""
        if is_pct:
            return f"{sign}{diff*100:.1f}%"
        return f"{sign}{diff:.3f}"
    
    m1 = r1.get("aggregate", r1.get("metrics", {}))
    m2 = r2.get("aggregate", r2.get("metrics", {}))
    
    print("\n📈 RETRIEVAL METRICS")
    print(f"   Recall@K:     {m1.get('recall_at_k', 0)*100:.1f}% → {m2.get('recall_at_k', 0)*100:.1f}%  ({delta(m1.get('recall_at_k', 0), m2.get('recall_at_k', 0), True)})")
    print(f"   Precision@K:  {m1.get('precision_at_k', 0)*100:.1f}% → {m2.get('precision_at_k', 0)*100:.1f}%  ({delta(m1.get('precision_at_k', 0), m2.get('precision_at_k', 0), True)})")
    print(f"   MRR:          {m1.get('mrr', 0):.3f} → {m2.get('mrr', 0):.3f}  ({delta(m1.get('mrr', 0), m2.get('mrr', 0))})")
    
    print("\n📝 GENERATION METRICS")
    print(f"   Groundedness: {m1.get('groundedness', 0)*100:.1f}% → {m2.get('groundedness', 0)*100:.1f}%  ({delta(m1.get('groundedness', 0), m2.get('groundedness', 0), True)})")
    print(f"   Correctness:  {m1.get('correctness', 0)*100:.1f}% → {m2.get('correctness', 0)*100:.1f}%  ({delta(m1.get('correctness', 0), m2.get('correctness', 0), True)})")
    
    print("\n⏱️  LATENCY METRICS")
    print(f"   Avg Total:    {m1.get('avg_latency_ms', 0):.0f}ms → {m2.get('avg_latency_ms', 0):.0f}ms")
    
    # Overall verdict
    score1 = (m1.get('recall_at_k', 0) + m1.get('mrr', 0) + m1.get('groundedness', 0)) / 3
    score2 = (m2.get('recall_at_k', 0) + m2.get('mrr', 0) + m2.get('groundedness', 0)) / 3
    
    print("\n" + "=" * 70)
    if score2 > score1:
        print(f"✅ IMPROVEMENT: Composite score {score1:.3f} → {score2:.3f} (+{(score2-score1)*100:.1f}%)")
    elif score2 < score1:
        print(f"⚠️  REGRESSION: Composite score {score1:.3f} → {score2:.3f} ({(score2-score1)*100:.1f}%)")
    else:
        print(f"➡️  NO CHANGE: Composite score {score1:.3f}")
    print("=" * 70)


async def run_evaluation(repo_id: int, use_reranker: bool = True, limit: Optional[int] = None) -> Dict:
    """Run evaluation and return metrics."""
    from eval.eval_dataset import get_eval_dataset, EvalQuestion
    from app.services.rag_service import search_similar_code, query_codebase
    from app.database import SessionLocal
    import time
    import re
    
    db = SessionLocal()
    dataset = get_eval_dataset()
    
    if limit:
        dataset = dataset[:limit]
    
    print(f"\n🔬 Running evaluation on {len(dataset)} questions...")
    print(f"   Reranker: {'Enabled' if use_reranker else 'Disabled'}")
    print("-" * 70)
    
    results = []
    top_k = 5
    
    for i, q in enumerate(dataset):
        print(f"[{i+1}/{len(dataset)}] {q.category}: {q.query[:45]}...", end=" ")
        
        try:
            start = time.time()
            
            # Retrieval
            chunks = search_similar_code(
                repo_id=repo_id,
                query=q.query,
                top_k=top_k,
                use_reranker=use_reranker
            )
            
            retrieval_time = (time.time() - start) * 1000
            
            # Calculate retrieval metrics
            retrieved_files = [
                c.get("metadata", {}).get("file_path", "").split("/")[-1].split("\\")[-1].lower()
                for c in chunks
            ]
            
            # Check for matches (partial matching)
            relevant_found = 0
            first_relevant_rank = 0
            for expected in q.expected_files:
                for rank, rf in enumerate(retrieved_files, 1):
                    if expected.lower() in rf:
                        relevant_found += 1
                        if first_relevant_rank == 0:
                            first_relevant_rank = rank
                        break
            
            recall = relevant_found / len(q.expected_files) if q.expected_files else 0
            precision = relevant_found / len(retrieved_files) if retrieved_files else 0
            mrr = 1.0 / first_relevant_rank if first_relevant_rank > 0 else 0
            
            # Generation
            gen_start = time.time()
            response = query_codebase(
                repo_id=repo_id,
                query=q.query,
                top_k=top_k
            )
            gen_time = (time.time() - gen_start) * 1000
            answer = response.get("answer", "")
            
            # Calculate generation metrics
            context = " ".join([c.get("content", "") for c in chunks]).lower()
            answer_lower = answer.lower()
            
            # Groundedness
            answer_words = set(re.findall(r'\b[a-zA-Z_]{4,}\b', answer_lower))
            grounded_words = sum(1 for w in answer_words if w in context)
            groundedness = grounded_words / len(answer_words) if answer_words else 0
            
            # Correctness
            found_keywords = sum(1 for kw in q.expected_keywords if kw.lower() in answer_lower)
            correctness = found_keywords / len(q.expected_keywords) if q.expected_keywords else 0
            
            total_time = retrieval_time + gen_time
            
            results.append({
                "id": q.id,
                "category": q.category,
                "recall": recall,
                "precision": precision,
                "mrr": mrr,
                "groundedness": groundedness,
                "correctness": correctness,
                "latency_ms": total_time,
                "error": None
            })
            
            status = "✓" if recall > 0 else "✗"
            print(f"{status} R:{recall:.0%} MRR:{mrr:.2f} G:{groundedness:.0%}")
            
        except Exception as e:
            print(f"❌ {str(e)[:30]}")
            results.append({
                "id": q.id,
                "category": q.category,
                "recall": 0,
                "precision": 0,
                "mrr": 0,
                "groundedness": 0,
                "correctness": 0,
                "latency_ms": 0,
                "error": str(e)
            })
    
    db.close()
    
    # Aggregate metrics
    successful = [r for r in results if not r.get("error")]
    n = len(successful)
    
    if n == 0:
        print("❌ No successful evaluations")
        return {"error": "No successful evaluations"}
    
    aggregate = {
        "recall_at_k": sum(r["recall"] for r in successful) / n,
        "precision_at_k": sum(r["precision"] for r in successful) / n,
        "mrr": sum(r["mrr"] for r in successful) / n,
        "groundedness": sum(r["groundedness"] for r in successful) / n,
        "correctness": sum(r["correctness"] for r in successful) / n,
        "avg_latency_ms": sum(r["latency_ms"] for r in successful) / n,
    }
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 EVALUATION RESULTS")
    print("=" * 70)
    print(f"   Questions: {n}/{len(dataset)}")
    print(f"\n📈 Retrieval")
    print(f"   Recall@{top_k}:     {aggregate['recall_at_k']*100:.1f}%")
    print(f"   Precision@{top_k}: {aggregate['precision_at_k']*100:.1f}%")
    print(f"   MRR:           {aggregate['mrr']:.3f}")
    print(f"\n📝 Generation")
    print(f"   Groundedness:  {aggregate['groundedness']*100:.1f}%")
    print(f"   Correctness:   {aggregate['correctness']*100:.1f}%")
    print(f"\n⏱️  Latency")
    print(f"   Average:       {aggregate['avg_latency_ms']:.0f}ms")
    print("=" * 70)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "repo_id": repo_id,
        "config": {
            "use_reranker": use_reranker,
            "top_k": top_k,
            "n_questions": len(dataset)
        },
        "aggregate": aggregate,
        "by_category": _aggregate_by_category(results),
        "details": results
    }


def _aggregate_by_category(results: List[Dict]) -> Dict:
    """Aggregate metrics by category."""
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    
    aggregated = {}
    for cat, items in categories.items():
        n = len([i for i in items if not i.get("error")])
        if n > 0:
            aggregated[cat] = {
                "recall": sum(i["recall"] for i in items if not i.get("error")) / n,
                "mrr": sum(i["mrr"] for i in items if not i.get("error")) / n,
                "count": n
            }
    return aggregated


async def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation - Change → Measure → Iterate")
    parser.add_argument("repo_id", type=int, nargs="?", help="Repository ID")
    parser.add_argument("--save", type=str, help="Save results to JSON file")
    parser.add_argument("--no-reranker", action="store_true", help="Disable reranker")
    parser.add_argument("--limit", type=int, help="Limit number of questions")
    parser.add_argument("--compare", nargs=2, metavar=("FILE1", "FILE2"), help="Compare two result files")
    
    args = parser.parse_args()
    
    # Comparison mode
    if args.compare:
        compare_results(args.compare[0], args.compare[1])
        return
    
    # Evaluation mode
    if not args.repo_id:
        parser.error("repo_id is required for evaluation")
    
    print("\n" + "=" * 70)
    print("🔬 RAG EVALUATION - Phase 0 Baseline")
    print("=" * 70)
    
    results = await run_evaluation(
        repo_id=args.repo_id,
        use_reranker=not args.no_reranker,
        limit=args.limit
    )
    
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to: {args.save}")
        print(f"\n💡 Next steps:")
        print(f"   1. Make a change to the system")
        print(f"   2. Run: python run_eval.py {args.repo_id} --save after.json")
        print(f"   3. Compare: python run_eval.py --compare {args.save} after.json")


if __name__ == "__main__":
    asyncio.run(main())
