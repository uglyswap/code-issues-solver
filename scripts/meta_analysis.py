#!/usr/bin/env python3
"""
Monthly meta-analysis script for Code Issues Solver.

This script analyzes bug patterns and successful patches to identify:
1. Recurring bug categories
2. High-success-rate patterns
3. Patterns that need manual validation
4. Knowledge base quality metrics

Run this script monthly to review and improve the knowledge base.

Usage:
    python scripts/meta_analysis.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/app')

from backend.app.database import async_session
from backend.app import crud, models
from sqlalchemy import select, func, desc


async def analyze_categories():
    """Analyze bug categories and their frequencies."""
    async with async_session() as db:
        # Count tickets by category
        result = await db.execute(
            select(
                models.Ticket.category,
                func.count(models.Ticket.id).label('count')
            )
            .group_by(models.Ticket.category)
            .order_by(desc('count'))
        )
        
        categories = result.all()
        
        print("\n" + "="*80)
        print("BUG CATEGORIES ANALYSIS")
        print("="*80)
        print(f"\n{'Category':<30} {'Count':<10} {'Percentage':<15}")
        print("-" * 80)
        
        total = sum(count for _, count in categories)
        for category, count in categories:
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{category:<30} {count:<10} {percentage:>6.1f}%")
        
        print("-" * 80)
        print(f"{'TOTAL':<30} {total:<10}")
        
        return categories


async def analyze_patterns():
    """Analyze bug patterns in the knowledge base."""
    async with async_session() as db:
        patterns = await crud.get_bug_patterns(db, skip=0, limit=100)
        
        print("\n" + "="*80)
        print("BUG PATTERNS ANALYSIS")
        print("="*80)
        print(f"\nTotal patterns in knowledge base: {len(patterns)}")
        
        if not patterns:
            print("\n⚠️  No patterns found. The knowledge base is empty.")
            print("   Consider creating patterns from successful patches.")
            return patterns
        
        # Group by success rate
        high_success = [p for p in patterns if p.success_rate >= 0.9]
        medium_success = [p for p in patterns if 0.7 <= p.success_rate < 0.9]
        low_success = [p for p in patterns if p.success_rate < 0.7]
        
        print(f"\n{'Success Rate':<30} {'Count':<10}")
        print("-" * 80)
        print(f"High (≥90%):                     {len(high_success):<10}")
        print(f"Medium (70-89%):                 {len(medium_success):<10}")
        print(f"Low (<70%):                      {len(low_success):<10}")
        
        # Show top patterns by occurrences
        print("\n" + "-" * 80)
        print("TOP 10 PATTERNS BY OCCURRENCES:")
        print("-" * 80)
        
        sorted_patterns = sorted(patterns, key=lambda p: p.occurrences, reverse=True)[:10]
        for i, pattern in enumerate(sorted_patterns, 1):
            print(f"\n{i}. {pattern.pattern_id}")
            print(f"   Category: {pattern.category}")
            print(f"   Description: {pattern.description[:80]}...")
            print(f"   Success rate: {pattern.success_rate:.0%} ({pattern.occurrences} occurrences)")
        
        # Identify patterns that need attention
        print("\n" + "-" * 80)
        print("PATTERNS NEEDING ATTENTION:")
        print("-" * 80)
        
        if low_success:
            print(f"\n⚠️  {len(low_success)} patterns with success rate < 70%:")
            for pattern in low_success[:5]:
                print(f"   - {pattern.pattern_id}: {pattern.success_rate:.0%} ({pattern.occurrences} occurrences)")
        else:
            print("\n✅ All patterns have success rate ≥ 70%")
        
        return patterns


async def analyze_successful_patches():
    """Analyze successful patches in the knowledge base."""
    async with async_session() as db:
        patches = await crud.get_successful_patches(db, skip=0, limit=100)
        
        print("\n" + "="*80)
        print("SUCCESSFUL PATCHES ANALYSIS")
        print("="*80)
        print(f"\nTotal successful patches: {len(patches)}")
        
        if not patches:
            print("\n⚠️  No successful patches found.")
            print("   Successful patches are automatically stored when bugs are verified as fixed.")
            return patches
        
        # Group by category
        by_category = defaultdict(list)
        for patch in patches:
            by_category[patch.category].append(patch)
        
        print(f"\n{'Category':<30} {'Count':<10}")
        print("-" * 80)
        for category, category_patches in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"{category:<30} {len(category_patches):<10}")
        
        # Show recent patches
        print("\n" + "-" * 80)
        print("RECENT SUCCESSFUL PATCHES (last 5):")
        print("-" * 80)
        
        recent_patches = sorted(patches, key=lambda p: p.created_at, reverse=True)[:5]
        for i, patch in enumerate(recent_patches, 1):
            print(f"\n{i}. {patch.title}")
            print(f"   Category: {patch.category}")
            print(f"   Created: {patch.created_at.strftime('%Y-%m-%d')}")
            print(f"   Files changed: {len(patch.files_changed) if patch.files_changed else 0}")
        
        return patches


async def suggest_patterns_from_patches():
    """Suggest creating patterns from successful patches."""
    async with async_session() as db:
        patches = await crud.get_successful_patches(db, skip=0, limit=100)
        patterns = await crud.get_bug_patterns(db, skip=0, limit=100)
        
        print("\n" + "="*80)
        print("SUGGESTIONS FOR NEW PATTERNS")
        print("="*80)
        
        if not patches:
            print("\nNo successful patches to analyze.")
            return
        
        # Group patches by category
        by_category = defaultdict(list)
        for patch in patches:
            by_category[patch.category].append(patch)
        
        # For each category, check if we have patterns
        suggestions = []
        for category, category_patches in by_category.items():
            category_patterns = [p for p in patterns if p.category == category]
            
            # If we have many patches but few patterns, suggest creating patterns
            if len(category_patches) >= 3 and len(category_patterns) < 2:
                suggestions.append({
                    'category': category,
                    'patch_count': len(category_patches),
                    'pattern_count': len(category_patterns)
                })
        
        if suggestions:
            print(f"\n💡 Found {len(suggestions)} categories that could benefit from new patterns:")
            print("-" * 80)
            
            for suggestion in suggestions:
                print(f"\nCategory: {suggestion['category']}")
                print(f"  Successful patches: {suggestion['patch_count']}")
                print(f"  Existing patterns: {suggestion['pattern_count']}")
                print(f"  → Consider creating 1-2 patterns from these patches")
        else:
            print("\n✅ All categories with multiple patches already have patterns")


async def generate_report():
    """Generate a comprehensive monthly report."""
    print("\n" + "="*80)
    print("CODE ISSUES SOLVER - MONTHLY META-ANALYSIS REPORT")
    print("="*80)
    print(f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    categories = await analyze_categories()
    patterns = await analyze_patterns()
    patches = await analyze_successful_patches()
    await suggest_patterns_from_patches()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    recommendations = []
    
    # Check if knowledge base is empty
    if not patterns:
        recommendations.append("🔴 CRITICAL: Knowledge base is empty. Start creating patterns from successful patches.")
    
    # Check for low-success patterns
    low_success = [p for p in patterns if p.success_rate < 0.7]
    if low_success:
        recommendations.append(f"🟡 WARNING: {len(low_success)} patterns have success rate < 70%. Review and improve them.")
    
    # Check for categories without patterns
    categories_with_patches = set(p.category for p in patches)
    categories_with_patterns = set(p.category for p in patterns)
    missing_patterns = categories_with_patches - categories_with_patterns
    
    if missing_patterns:
        recommendations.append(f"🟡 INFO: {len(missing_patterns)} categories have successful patches but no patterns: {', '.join(missing_patterns)}")
    
    if not recommendations:
        recommendations.append("✅ Knowledge base is healthy. No immediate action needed.")
    
    print("\n" + "-" * 80)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec}")
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(generate_report())