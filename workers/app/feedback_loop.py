"""
Feedback loop module - structured feedback between reviewer and coder.
"""
from typing import Dict, List, Optional
import json


def parse_reviewer_feedback(review_result: Dict) -> Dict:
    """
    Parse reviewer feedback into structured format.
    
    Expected review_result format:
    {
        "review_status": "approved|changes_requested|rejected",
        "rejection_reason": "incomplete_analysis|poor_analysis_quality|bad_patch|tests_failed|none",
        "pass1_analysis_completeness": {...},
        "pass2_analysis_quality": {...},
        "pass3_patch_review": {...},
        "final_decision": {
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...],
            "suggestions": [...],
            "next_steps": [...]
        }
    }
    
    Returns:
        {
            "approved": bool,
            "rejection_reason": str,
            "feedback": {
                "step1_context_analysis": {
                    "status": "pass|fail",
                    "missing": [...],
                    "suggestions": [...]
                },
                "step2_root_cause_diagnosis": {...},
                "step3_patch_proposal": {...},
                "step4_justification": {...}
            },
            "test_feedback": {...},
            "overall_feedback": "...",
            "next_steps": [...]
        }
    """
    feedback = {
        "approved": review_result.get("review_status") == "approved",
        "rejection_reason": review_result.get("rejection_reason", "none"),
        "feedback": {},
        "test_feedback": None,
        "overall_feedback": "",
        "next_steps": []
    }
    
    # Parse pass 1 (completeness)
    pass1 = review_result.get("pass1_analysis_completeness", {})
    if pass1.get("status") == "fail":
        feedback["feedback"]["step1_context_analysis"] = {
            "status": "fail",
            "missing": pass1.get("missing_sections", []),
            "suggestions": [
                "Provide complete analysis for all 4 steps before proposing a patch",
                "Each step should have sufficient detail (see coder.md for requirements)"
            ]
        }
    
    # Parse pass 2 (quality)
    pass2 = review_result.get("pass2_analysis_quality", {})
    if pass2.get("status") == "fail":
        feedback["feedback"]["step2_root_cause_diagnosis"] = {
            "status": "fail",
            "missing": pass2.get("issues", []),
            "suggestions": [
                "Improve the quality of your root cause analysis",
                "Be more specific about why the bug occurs",
                "Identify the actual root cause, not just the symptom"
            ]
        }
    
    # Parse pass 3 (patch review)
    pass3 = review_result.get("pass3_patch_review", {})
    final_decision = review_result.get("final_decision", {})
    
    if pass3.get("status") == "fail":
        feedback["feedback"]["step3_patch_proposal"] = {
            "status": "fail",
            "missing": pass3.get("issues", []),
            "suggestions": final_decision.get("suggestions", [])
        }
    
    # Add test feedback if present
    if "test_results" in review_result:
        feedback["test_feedback"] = review_result["test_results"]
    
    # Overall feedback
    feedback["overall_feedback"] = final_decision.get("summary", "")
    feedback["next_steps"] = final_decision.get("next_steps", [])
    
    return feedback


def format_feedback_for_coder(feedback: Dict, attempt: int) -> str:
    """
    Format feedback into a prompt for the coder agent.
    
    Args:
        feedback: Parsed feedback dict
        attempt: Current attempt number (1, 2, or 3)
    
    Returns:
        Formatted feedback string to include in coder prompt
    """
    if feedback["approved"]:
        return ""
    
    parts = []
    
    # Header
    parts.append(f"## FEEDBACK FROM REVIEWER (Attempt {attempt}/3)\n")
    parts.append(f"**Status**: {'APPROVED' if feedback['approved'] else 'REJECTED'}")
    parts.append(f"**Reason**: {feedback['rejection_reason']}\n")
    
    # Overall feedback
    if feedback["overall_feedback"]:
        parts.append(f"### Overall Feedback\n{feedback['overall_feedback']}\n")
    
    # Step-specific feedback
    if feedback["feedback"]:
        parts.append("### Issues to Fix\n")
        
        for step, step_feedback in feedback["feedback"].items():
            if step_feedback.get("status") == "fail":
                parts.append(f"**{step.replace('_', ' ').title()}**:")
                
                if step_feedback.get("missing"):
                    parts.append("Missing or incomplete:")
                    for item in step_feedback["missing"]:
                        parts.append(f"  - {item}")
                
                if step_feedback.get("suggestions"):
                    parts.append("Suggestions:")
                    for suggestion in step_feedback["suggestions"]:
                        if isinstance(suggestion, dict):
                            parts.append(f"  - {suggestion.get('comment', suggestion)}")
                        else:
                            parts.append(f"  - {suggestion}")
                
                parts.append("")
    
    # Test feedback
    if feedback["test_feedback"]:
        parts.append("### Test Results\n")
        test_results = feedback["test_feedback"]
        
        if not test_results.get("success"):
            parts.append("**Tests FAILED**\n")
            
            if test_results.get("errors"):
                parts.append("Errors:")
                for error in test_results["errors"]:
                    parts.append(f"  - {error}")
            
            if test_results.get("output"):
                parts.append(f"\nTest output:\n```\n{test_results['output'][:1000]}\n```\n")
    
    # Next steps
    if feedback["next_steps"]:
        parts.append("### Next Steps\n")
        for i, step in enumerate(feedback["next_steps"], 1):
            parts.append(f"{i}. {step}")
        parts.append("")
    
    # Attempt warning
    if attempt == 3:
        parts.append("\n⚠️ **WARNING**: This is your FINAL attempt. If this patch is rejected, the ticket will be marked as failed.")
    elif attempt == 2:
        parts.append("\n⚠️ This is your second attempt. Please carefully address all feedback.")
    
    return "\n".join(parts)


def should_retry_patch(review_result: Dict, attempt: int, max_attempts: int = 3) -> bool:
    """
    Determine if the patch should be retried based on review results.
    
    Args:
        review_result: Review result dict
        attempt: Current attempt number
        max_attempts: Maximum number of attempts allowed
    
    Returns:
        True if should retry, False otherwise
    """
    # Don't retry if approved
    if review_result.get("review_status") == "approved":
        return False
    
    # Don't retry if max attempts reached
    if attempt >= max_attempts:
        return False
    
    # Don't retry if rejection reason is "tests_failed" and we've tried 2 times
    # (tests should pass after 2 attempts)
    if review_result.get("rejection_reason") == "tests_failed" and attempt >= 2:
        return False
    
    return True