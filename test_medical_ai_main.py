#!/usr/bin/env python3
"""Test the main newsletter generation workflow with 의료 AI topic."""

from datetime import datetime
from src.main import run_newsletter_generation

print("=" * 60)
print("🧪 Testing Newsletter Generation: 의료 AI")
print("=" * 60)
print()

# Define user context for medical AI research
user_context = {
    "topic": "의료 AI",
    "topic_description": "의료 진단, 치료, 신약 개발을 돕는 인공지능 시스템",
    "subtopics": ["의료 영상 진단", "질병 예측", "신약 개발"],
    "preferred_sources": ["papers", "news", "blogs"],
    "goal": "learning",
    "difficulty": "intermediate",
}

print("📋 User Context:")
print("-" * 60)
for key, value in user_context.items():
    print(f"  {key}: {value}")
print()

# Generate test date
test_date = datetime.now().strftime("%Y-%m-%d")

print(f"🚀 Starting newsletter generation for {test_date}...")
print()

# Run the newsletter generation with personalized context
result = run_newsletter_generation(
    target_date=test_date,
    user_context=user_context
)

print()
print("=" * 60)
print("✅ Newsletter generation completed!")
print("=" * 60)

if result:
    print(f"\nCheck the generated files in: articles/{test_date}/")
