from csp import create_day_schedule
import copy


def simulate_roaster(day_no, total_no_days, config, inputs, constraints):
    """
    Recursively generates roaster schedule day by day with backtracking.
    
    Optimizations:
    - Reduced memory copies (only copy what's necessary)
    - Early termination when threshold reached
    - Better state management
    """
    # Base case: all days scheduled
    if day_no == total_no_days:
        return inputs["schedule"], inputs["quality_count"]
    
    solutions = []
    max_attempts = config.get("threshold", 10)
    print(f"\nIteration {day_no + 1}/{total_no_days}:")
    
    while len(solutions) < max_attempts:
        # Try to find a solution for current day
        # Pass current day number so CSP can check for leaves
        solution, quality_count = create_day_schedule(config, inputs, constraints, solutions, current_day=day_no)
        
        if solution is None:
            # No more solutions possible for this day
            return None, None
        
        # Found a solution, add it to tried solutions
        solutions.append(solution)
        
        # Prepare state for next day (optimized: only copy what changes)
        # Store current solution in schedule temporarily
        current_schedule = inputs["schedule"] + [solution]
        
        # Create minimal new_input dict (avoid deep copy of entire structure)
        new_input = {
            "shift_day": [val + 1 for val in inputs["shift_day"]],  # Increment day counter
            "work_pattern": inputs["work_pattern"],  # Reference (immutable in practice)
            "previous_day": solution,  # Current day's solution becomes previous
            "quality_count": quality_count,  # Updated quality counts
            "schedule": current_schedule,  # Current schedule state
            "employee_leaves": inputs.get("employee_leaves", []),  # Pass leave information
            "shift_preferences": inputs.get("shift_preferences", []),  # Pass shift preferences
            "shift_exclusions": inputs.get("shift_exclusions", [])  # Pass shift exclusions
        }
        
        # Recursively solve remaining days
        added_schedule, final_quality_count = simulate_roaster(
            day_no + 1, total_no_days, config, new_input, constraints
        )
        
        if added_schedule is not None:
            # Success! Return the complete schedule
            return added_schedule, final_quality_count
        # else: backtrack and try next solution
    
    # Exhausted all solution attempts for this day
    return None, None