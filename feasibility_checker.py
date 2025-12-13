"""
Feasibility checker for roaster generation.
Detects impossible input configurations before attempting to solve.
"""


def check_feasibility(config, inputs, constraints, no_days):
    """
    Check if the roaster generation problem is feasible.
    
    Returns:
        (is_feasible, list_of_warnings) where warnings are strings describing issues
    """
    warnings = []
    errors = []
    
    # Check 1: Minimum staffing requirements per day
    total_min_required = sum(constraints["min_count"].values())
    total_max_allowed = sum(constraints["max_count"].values())
    
    if total_min_required > config["no_employees"]:
        errors.append(
            f"INFEASIBLE: Total minimum employees required ({total_min_required}) exceeds "
            f"total employees ({config['no_employees']})"
        )
    
    if total_max_allowed < total_min_required:
        errors.append(
            f"INFEASIBLE: Total maximum employees ({total_max_allowed}) is less than "
            f"total minimum required ({total_min_required})"
        )
    
    # Check 2: Day-by-day feasibility (considering leaves, work patterns, shift preferences, and shift exclusions)
    employee_leaves = inputs.get("employee_leaves", [])
    shift_preferences = inputs.get("shift_preferences", [])
    shift_exclusions = inputs.get("shift_exclusions", [])
    
    for day in range(no_days):
        # Count available employees for this day (overall)
        available_employees = []
        unavailable_reasons = {}
        
        # Count available employees per shift (considering shift preferences and exclusions)
        available_per_shift = {shift_id: [] for shift_id in constraints["min_count"].keys()}
        
        for i in range(config["no_employees"]):
            # Check if on leave
            if i < len(employee_leaves) and day in employee_leaves[i]:
                unavailable_reasons[i] = "on leave"
                continue
            
            # Check work pattern
            # shift_day gets incremented each day in generate_roaster, so we simulate that
            pattern_id = inputs["work_pattern"][i]
            pattern = config["work_pattern"][pattern_id]
            initial_shift_day = inputs["shift_day"][i]
            
            # Calculate what day this would be in the pattern cycle
            # shift_day increments by 1 each day, so after 'day' days, it's initial + day
            current_shift_day = initial_shift_day + day
            pattern_day = current_shift_day % pattern["total_days"]
            
            if pattern_day in pattern["off_days"]:
                unavailable_reasons[i] = "work pattern off day"
                continue
            
            # Employee is available (not on leave, not on work pattern off day)
            available_employees.append(i)
            
            # Check shift preferences and exclusions: can this employee work each shift?
            employee_prefs = shift_preferences[i] if i < len(shift_preferences) else set()
            employee_exclusions = shift_exclusions[i] if i < len(shift_exclusions) else set()
            
            for shift_id in constraints["min_count"].keys():
                # Employee can work this shift if:
                # - Shift is NOT in their exclusion list, AND
                # - (They have no preferences (empty set = can work any shift), OR this shift is in their preference list)
                if shift_id in employee_exclusions:
                    # Employee cannot work this shift (excluded)
                    continue
                
                if not employee_prefs or shift_id in employee_prefs:
                    available_per_shift[shift_id].append(i)
        
        num_available = len(available_employees)
        
        # Check if we have enough employees for minimum requirements (overall)
        if num_available < total_min_required:
            errors.append(
                f"INFEASIBLE: Day {day + 1}: Only {num_available} employees available "
                f"but {total_min_required} minimum required. "
                f"Unavailable: {dict(list(unavailable_reasons.items())[:5])}"
            )
        
        # Check if we have enough for each shift's minimum (considering shift preferences)
        for shift_id, min_req in constraints["min_count"].items():
            num_available_for_shift = len(available_per_shift[shift_id])
            if num_available_for_shift < min_req:
                errors.append(
                    f"INFEASIBLE: Day {day + 1}, Shift {shift_id}: Only {num_available_for_shift} employees "
                    f"available (considering shift preferences) but {min_req} minimum required"
                )
            elif num_available_for_shift == min_req:
                warnings.append(
                    f"WARNING: Day {day + 1}, Shift {shift_id}: Exactly {num_available_for_shift} employees "
                    f"available for {min_req} minimum requirement (no flexibility, considering shift preferences and exclusions)"
                )
        
        # Warning if close to minimum (overall)
        if num_available == total_min_required:
            warnings.append(
                f"WARNING: Day {day + 1}: Exactly {num_available} employees available "
                f"for {total_min_required} minimum requirement (no flexibility)"
            )
        elif num_available < total_min_required + 2:
            warnings.append(
                f"WARNING: Day {day + 1}: Only {num_available} employees available "
                f"for {total_min_required} minimum requirement (very tight)"
            )
    
    # Check 3: Forbidden shift sequence impact
    # Count how many employees are blocked from certain shifts due to previous day
    if "previous_day" in inputs:
        forbidden_blocks = {}  # shift_id -> count of employees blocked
        
        for k_val, forbidden_val in config["forbidden_constraints"]:
            # Count employees who worked k_val yesterday
            employees_with_k = sum(1 for prev in inputs["previous_day"] if prev == k_val)
            
            if forbidden_val not in forbidden_blocks:
                forbidden_blocks[forbidden_val] = 0
            forbidden_blocks[forbidden_val] += employees_with_k
        
        # Check if forbidden constraints block too many employees from a shift
        for shift_id, min_req in constraints["min_count"].items():
            blocked = forbidden_blocks.get(shift_id, 0)
            if blocked > config["no_employees"] - min_req:
                warnings.append(
                    f"WARNING: Shift {shift_id}: {blocked} employees may be blocked by "
                    f"forbidden constraints, but {min_req} minimum required. "
                    f"May be infeasible depending on other constraints."
                )
    
    # Check 4: Work pattern distribution
    # Check if work patterns cause too many employees to be off on the same days
    pattern_off_counts = {}  # day -> count of employees off due to pattern
    
    for day in range(no_days):
        pattern_off_count = 0
        for i in range(config["no_employees"]):
            # Skip if on leave (already counted)
            if i < len(employee_leaves) and day in employee_leaves[i]:
                continue
            
            pattern_id = inputs["work_pattern"][i]
            pattern = config["work_pattern"][pattern_id]
            initial_shift_day = inputs["shift_day"][i]
            current_shift_day = initial_shift_day + day
            pattern_day = current_shift_day % pattern["total_days"]
            
            if pattern_day in pattern["off_days"]:
                pattern_off_count += 1
        
        pattern_off_counts[day] = pattern_off_count
        available = config["no_employees"] - pattern_off_count
        
        # Subtract leave count for this day
        leave_count = sum(1 for i in range(config["no_employees"]) 
                         if i < len(employee_leaves) and day in employee_leaves[i])
        available -= leave_count
        
        if available < total_min_required:
            errors.append(
                f"INFEASIBLE: Day {day + 1}: {pattern_off_count} employees off due to work pattern, "
                f"{leave_count} on leave, only {available} available for {total_min_required} minimum"
            )
    
    # Check 5: Shift-specific feasibility
    # For each shift, check if enough employees can work it considering all constraints
    for shift_id in range(1, config["no_shifts"] + 1):
        min_req = constraints["min_count"].get(shift_id, 0)
        max_allowed = constraints["max_count"].get(shift_id, config["no_employees"])
        
        if min_req > max_allowed:
            errors.append(
                f"INFEASIBLE: Shift {shift_id}: min_count ({min_req}) > max_count ({max_allowed})"
            )
        
        if min_req > config["no_employees"]:
            errors.append(
                f"INFEASIBLE: Shift {shift_id}: min_count ({min_req}) > total employees "
                f"({config['no_employees']})"
            )
    
    # Check 6: Leave concentration
    # Check if too many employees are on leave on the same days
    leave_counts = {}  # day -> count of employees on leave
    for day in range(no_days):
        count = sum(1 for i in range(config["no_employees"]) 
                   if i < len(employee_leaves) and day in employee_leaves[i])
        leave_counts[day] = count
        
        available = config["no_employees"] - count
        if available < total_min_required:
            errors.append(
                f"INFEASIBLE: Day {day + 1}: {count} employees on leave, "
                f"only {available} available for {total_min_required} minimum requirement"
            )
        elif available == total_min_required:
            warnings.append(
                f"WARNING: Day {day + 1}: {count} employees on leave, "
                f"exactly {available} available (no flexibility)"
            )
    
    return len(errors) == 0, errors + warnings


def check_feasibility_per_day(config, inputs, constraints, day, employee_leaves=None, shift_preferences=None, shift_exclusions=None):
    """
    Check feasibility for a specific day.
    Useful for checking during scheduling.
    
    Returns:
        (is_feasible, reason_string)
    """
    if employee_leaves is None:
        employee_leaves = inputs.get("employee_leaves", [])
    if shift_preferences is None:
        shift_preferences = inputs.get("shift_preferences", [])
    if shift_exclusions is None:
        shift_exclusions = inputs.get("shift_exclusions", [])
    
    # Count available employees (overall)
    available_count = 0
    # Count available employees per shift (considering shift preferences and exclusions)
    available_per_shift = {shift_id: 0 for shift_id in constraints["min_count"].keys()}
    
    for i in range(config["no_employees"]):
        # Check leave
        if i < len(employee_leaves) and day in employee_leaves[i]:
            continue
        
        # Check work pattern
        pattern_id = inputs["work_pattern"][i]
        pattern = config["work_pattern"][pattern_id]
        initial_shift_day = inputs["shift_day"][i]
        current_shift_day = initial_shift_day + day
        pattern_day = current_shift_day % pattern["total_days"]
        
        if pattern_day in pattern["off_days"]:
            continue
        
        # Employee is available
        available_count += 1
        
        # Check shift preferences and exclusions
        employee_prefs = shift_preferences[i] if i < len(shift_preferences) else set()
        employee_exclusions = shift_exclusions[i] if i < len(shift_exclusions) else set()
        
        for shift_id in constraints["min_count"].keys():
            # Employee can work this shift if:
            # - Shift is NOT in their exclusion list, AND
            # - (No preferences or shift in preferences)
            if shift_id in employee_exclusions:
                continue  # Excluded shift
            
            if not employee_prefs or shift_id in employee_prefs:
                available_per_shift[shift_id] += 1
    
    total_min_required = sum(constraints["min_count"].values())
    
    if available_count < total_min_required:
        return False, (
            f"Day {day + 1}: Only {available_count} employees available "
            f"but {total_min_required} minimum required"
        )
    
    # Check each shift (considering shift preferences)
    for shift_id, min_req in constraints["min_count"].items():
            if available_per_shift[shift_id] < min_req:
                return False, (
                    f"Day {day + 1}, Shift {shift_id}: Only {available_per_shift[shift_id]} employees available "
                    f"(considering shift preferences and exclusions) but {min_req} minimum required"
                )
    
    return True, ""

