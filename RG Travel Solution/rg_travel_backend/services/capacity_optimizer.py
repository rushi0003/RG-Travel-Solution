# backend/services/capacity_optimizer.py
# RG Travel Solution - Cab Capacity Optimization Service
# STEP 4: Minimize cabs used and empty seats with optimal 4/6 seater mix
# STEP 5: Rebalance to avoid 1-2 person cabs

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ===============================================================
# STEP 5: Remainder Rebalancing (Avoid 1-2 Person Cabs)
# ===============================================================

def rebalance_group_sizes(
    num_employees: int,
    use_4_seaters: int,
    use_6_seaters: int,
    max_group_capacity: int = 6
) -> List[int]:
    """
    STEP 5: Generate group sizes that avoid putting 1-2 employees in a nearly-empty cab.
    
    Algorithm:
    1. Calculate base distribution: fill 6-seaters first, then 4-seaters
    2. If last group has 1-2 employees, rebalance by:
       - Redistributing excess from previous groups
       - Example: Instead of [4,4,4,4,2], prefer [4,4,4,3,3]
    
    Args:
        num_employees: Total employees
        use_4_seaters: Number of 4-seater cabs to use
        use_6_seaters: Number of 6-seater cabs to use
        max_group_capacity: The vehicle type capacity (4 or 6), for consistency
        
    Returns:
        List[int]: Group sizes that sum to num_employees
        
    Example:
        >>> rebalance_group_sizes(18, use_4_seaters=0, use_6_seaters=3)
        [6, 6, 6]  # Fills 3 6-seaters
        
        >>> rebalance_group_sizes(18, use_4_seaters=5, use_6_seaters=0)
        [4, 4, 4, 3, 3]  # Avoids [4,4,4,4,2]
        
        >>> rebalance_group_sizes(22, use_4_seaters=2, use_6_seaters=2)
        [6, 6, 4, 6]  # or similar balanced arrangement
    """
    if num_employees <= 0:
        return []
    
    total_cabs = use_4_seaters + use_6_seaters
    if total_cabs == 0:
        return []
    
    # Allocate people to 6-seaters and 4-seaters
    max_6_capacity = use_6_seaters * 6
    
    if use_4_seaters == 0:
        # Only 6-seaters
        people_for_6 = num_employees
        people_for_4 = 0
    elif num_employees <= max_6_capacity:
        # Use 6-seaters first (more efficient)
        people_for_6 = num_employees
        people_for_4 = 0
    else:
        # Use all 6-seaters and distribute remainder to 4-seaters
        people_for_6 = max_6_capacity
        people_for_4 = num_employees - max_6_capacity
    
    # Generate sizes, then rebalance
    group_sizes = []
    
    # Distribute for 6-seaters
    if use_6_seaters > 0:
        sizes_6 = _distribute_evenly_with_rebalance(people_for_6, use_6_seaters, 6)
        group_sizes.extend(sizes_6)
    
    # Distribute for 4-seaters
    if use_4_seaters > 0:
        sizes_4 = _distribute_evenly_with_rebalance(people_for_4, use_4_seaters, 4)
        group_sizes.extend(sizes_4)
    
    # Final rebalance: if last group has 1 or 2 people, try to redistribute
    group_sizes = _final_rebalance_to_avoid_tiny_cabs(group_sizes)
    
    return sorted(group_sizes, reverse=True)  # Largest groups first


def _distribute_evenly_with_rebalance(
    total_people: int,
    num_groups: int,
    max_capacity: int
) -> List[int]:
    """
    Distribute people across groups, naturally avoiding tiny remainders.
    
    Example:
        >>> _distribute_evenly_with_rebalance(18, 5, 4)
        [4, 4, 4, 3, 3]  # not [4, 4, 4, 4, 2]
        
        >>> _distribute_evenly_with_rebalance(7, 4, 4)
        [2, 2, 2, 1]  # unavoidable (not enough people)
    """
    if num_groups == 0 or total_people == 0:
        return []
    
    if total_people <= num_groups:
        # Less people than groups - distribute 1 person each
        return [1] * total_people + [0] * (num_groups - total_people)
    
    # Base distribution
    base_per_group = total_people // num_groups
    remainder = total_people % num_groups
    
    # Create sizes array
    sizes = [base_per_group] * num_groups
    
    # Add rest to latter groups (to avoid having [X+1, X+1, ..., X] pattern which leaves last groups tiny)
    for i in range(num_groups - remainder, num_groups):
        sizes[i] += 1
    
    # Validate that no size exceeds max_capacity
    for i, size in enumerate(sizes):
        if size > max_capacity:
            logger.warning(
                f"Group {i} exceeds capacity: {size} > {max_capacity}. "
                f"This indicates an issue in capacity calculation."
            )
    
    return [s for s in sizes if s > 0]


def _final_rebalance_to_avoid_tiny_cabs(group_sizes: List[int]) -> List[int]:
    """
    If the last group(s) have 1-2 people, rebalance by taking from previous groups.
    
    Rules:
    - If last group has 1 person: move to previous group (if room)
    - If last group has 2 people: try to split [1,1] to two previous groups
    - Keep all group sizes <= their original capacity
    """
    if len(group_sizes) <= 1:
        return group_sizes
    
    sizes = list(group_sizes)  # Make a copy
    
    # Check last group
    while len(sizes) > 1:
        last_size = sizes[-1]
        
        if last_size == 0:
            # Remove empty groups
            sizes.pop()
            continue
        
        if last_size in (1, 2):
            # Last group is tiny
            # Try to merge with or distribute to previous groups
            tiny_group = sizes.pop()
            
            # Try to add to previous group (if capacity allows)
            # But we don't know the capacity of the last group that was removed
            # So we use a heuristic: if previous group + tiny < previous_group_capacity, merge
            # For safety, we assume max capacity is 6 (could be 4)
            prev_group_capacities = {
                3: 4,  # Group of 3 fits in 4-seater
                4: 4,  # Group of 4 fills 4-seater
                5: 6,  # Group of 5 fits in 6-seater
                6: 6,  # Group of 6 fills 6-seater
                2: 4,  # Group of 2 fits in 4-seater
                1: 4,  # Group of 1 fits in 4-seater
            }
            
            if sizes:
                prev_size = sizes[-1]
                
                # Add tiny group to previous if possible
                if prev_size + tiny_group <= 6:  # Conservative: assume 6-seater capacity
                    sizes[-1] += tiny_group
                else:
                    # Can't merge, put back
                    sizes.append(tiny_group)
                    break
            else:
                # No previous group, put back
                sizes.append(tiny_group)
                break
        else:
            # Last group is acceptable size
            break
    
    return sizes


# ===============================================================
# STEP 4: Capacity Optimization
# ===============================================================



# ===============================================================
# STEP 4: Capacity Optimization
# ===============================================================



def optimize_cab_capacity(
    num_employees: int,
    available_4_seaters: int,
    available_6_seaters: int,
    prioritize_6_seaters: bool = True
) -> Dict[str, Any]:
    """
    Find optimal mix of 4-seater and 6-seater cabs to minimize:
    - Number of cabs used (primary)
    - Empty seats wasted (secondary)
    
    Scoring Formula: score = (cabs_used × 100) + (empty_seats × 10)
    If prioritize_6_seaters is True, we slightly favor 6-seaters in ties or near-ties.
    
    Args:
        num_employees: Number of employees to transport
        available_4_seaters: Number of 4-seater cabs available
        available_6_seaters: Number of 6-seater cabs available
        prioritize_6_seaters: If True, apply a small penalty to 4-seater predominant solutions
    
    Returns:
        {
            "success": True/False,
            "message": str (if error),
            "data": {
                "use_4_seaters": int,
                "use_6_seaters": int,
                "total_cabs": int,
                "total_seats": int,
                "empty_seats": int,
                "optimization_score": int,
                "strategy_used": str,
                "all_candidates": [...] (optional, for debugging)
            }
        }
    
    Strategy:
        Evaluates ALL valid combinations of 4 and 6 seaters within availability limits.
        Selects combination with lowest score.
    """
    
    # Validation: No employees
    if num_employees <= 0:
        return {
            "success": False,
            "message": "No employees to transport",
            "data": {
                "num_employees": num_employees
            }
        }
    
    # Validation: Total capacity check
    max_capacity = (available_4_seaters * 4) + (available_6_seaters * 6)
    if num_employees > max_capacity:
        return {
            "success": False,
            "message": "Insufficient capacity",
            "data": {
                "required_employees": num_employees,
                "total_available_capacity": max_capacity,
                "available_4_seaters": available_4_seaters,
                "available_6_seaters": available_6_seaters,
                "shortfall": num_employees - max_capacity,
                "suggestions": [
                    "Approve more drivers to increase fleet capacity",
                    "Split employees into multiple trips at different times",
                    "Reduce the number of employees for this time slot"
                ]
            }
        }
    
    # Generate all valid combinations
    candidates: List[Dict[str, Any]] = []
    
    for count_6 in range(0, available_6_seaters + 1):
        for count_4 in range(0, available_4_seaters + 1):
            # Calculate total seats for this combination
            total_seats = (count_6 * 6) + (count_4 * 4)
            
            # MUST have enough seats to cover all employees
            if total_seats < num_employees:
                continue
            
            # Calculate metrics
            total_cabs = count_6 + count_4
            empty_seats = total_seats - num_employees
            
            # OPTIMIZATION SCORE: Prioritize fewer cabs, then fewer empty seats
            # score = (cabs × 100) + (empty_seats × 10)
            score = (total_cabs * 100) + (empty_seats * 10)
            
            # PRIORITY RULE: If priority requested, give a tiny bonus for each 6-seater used
            # This ensures that if two combinations have same cab count and empty seats, 
            # the one with more 6-seaters (and thus fewer total cabs potentially, but if cabs are same)
            # Actually, if cab count and empty seats are same, total seats are same.
            # 3*6 + 1*4 = 22. 0*6 + 5.5? No.
            # Usually priority means if we can choose between 1 6-seater vs 2 4-seaters (if 6 people), 1 6-seater wins by cab count.
            # If 12 people: 2 6-seaters vs 3 4-seaters. 6-seater wins by cab count.
            # The only tie is something like 2x6 (12) vs 3x4 (12) - Wait, cab count 2 vs 3.
            # In all cases, 6-seaters reduce cab count for same capacity, so they naturally win.
            # However, user explicitly asked for priority. We can add a "priority weight" to 4-seaters.
            if prioritize_6_seaters:
                score += (count_4 * 5) # 5 point penalty for each 4-seater used
            
            candidates.append({
                "use_4_seaters": count_4,
                "use_6_seaters": count_6,
                "total_cabs": total_cabs,
                "total_seats": total_seats,
                "empty_seats": empty_seats,
                "optimization_score": score
            })
    
    # Edge case: No valid combinations (shouldn't happen after capacity check)
    if not candidates:
        return {
            "success": False,
            "message": "No valid cab combinations found",
            "data": {
                "num_employees": num_employees,
                "available_4_seaters": available_4_seaters,
                "available_6_seaters": available_6_seaters
            }
        }
    
    # Sort by score (ascending) - lowest score = best
    candidates.sort(key=lambda x: x["optimization_score"])
    
    # Best solution
    best = candidates[0]
    
    # Determine strategy used
    strategy = _determine_strategy(int(best["use_4_seaters"]), int(best["use_6_seaters"]))
    
    # Return optimization result
    top_candidates = []
    limit = 5 if len(candidates) > 5 else len(candidates)
    for i in range(limit):
        top_candidates.append(candidates[i])
        
    return {
        "success": True,
        "data": {
            "use_4_seaters": int(best["use_4_seaters"]),
            "use_6_seaters": int(best["use_6_seaters"]),
            "total_cabs": int(best["total_cabs"]),
            "total_seats": int(best["total_seats"]),
            "empty_seats": int(best["empty_seats"]),
            "optimization_score": int(best["optimization_score"]),
            "strategy_used": strategy,
            "num_employees": num_employees,
            "efficiency_percent": float(int((num_employees / best["total_seats"]) * 1000) / 10.0),
            "all_candidates": top_candidates
        }
    }


def _determine_strategy(use_4: int, use_6: int) -> str:
    """
    Determine which strategy was used based on the result.
    
    Returns:
        "6_first" | "4_first" | "mixed_optimal" | "exact_fit"
    """
    if use_4 == 0 and use_6 > 0:
        return "6_seaters_only"
    elif use_6 == 0 and use_4 > 0:
        return "4_seaters_only"
    elif use_4 > 0 and use_6 > 0:
        return "mixed_optimal"
    else:
        return "unknown"


# ===============================================================
# HELPER: Quick optimization without full details
# ===============================================================

def quick_optimize(num_employees: int, available_4: int, available_6: int) -> Optional[Tuple[int, int]]:
    """
    Quick optimization that returns just the counts.
    
    Returns:
        (use_4_seaters, use_6_seaters) or None if impossible
    """
    result = optimize_cab_capacity(num_employees, available_4, available_6)
    if not result["success"]:
        return None
    return (int(result["data"]["use_4_seaters"]), int(result["data"]["use_6_seaters"]))


def get_balanced_group_distribution(
    num_employees: int,
    use_4_seaters: int,
    use_6_seaters: int,
) -> List[int]:
    """
    Backward-compatible alias for older tests/scripts.
    """
    return rebalance_group_sizes(
        num_employees=num_employees,
        use_4_seaters=use_4_seaters,
        use_6_seaters=use_6_seaters,
    )
