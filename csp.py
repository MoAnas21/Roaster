from ortools.sat.python import cp_model
import math
import copy


def create_day_schedule(config, inputs, constraints, prev_solutions=None, current_day=None):
    """
    Creates an optimal day schedule using constraint programming.
    
    Fixed issues:
    - Quality count indexing bug (was using [shift] instead of [employee][shift])
    - Improved quality metric (minimize variance instead of exponential)
    - Optimized CSP model (reuse indicator variables)
    - Better search strategy
    
    Args:
        current_day: Day index (0-based) for checking leave constraints
    """
    if prev_solutions is None:
        prev_solutions = []
    
    # Validate inputs
    if len(inputs["quality_count"]) != config["no_employees"]:
        raise ValueError(f"quality_count length ({len(inputs['quality_count'])}) doesn't match number of employees ({config['no_employees']})")
    
    model = cp_model.CpModel()
    
    # Initialize variables: x[i] = shift assigned to employee i (0 = off)
    x = [model.NewIntVar(0, config["no_shifts"], f'x{i}') for i in range(config["no_employees"])]
    
    # Create indicator variables for each shift value (reused for constraints and quality)
    # indicators[value][i] = 1 if employee i is assigned shift value
    indicators = {}
    for value in range(1, config["no_shifts"] + 1):
        indicators[value] = [model.NewBoolVar(f'ind_{i}_{value}') for i in range(config["no_employees"])]
        
        for i in range(config["no_employees"]):
            # Link indicator to variable
            model.Add(x[i] == value).OnlyEnforceIf(indicators[value][i])
            model.Add(x[i] != value).OnlyEnforceIf(indicators[value][i].Not())
        
        # Add min/max count constraints for this shift
        model.Add(sum(indicators[value]) >= constraints["min_count"][value])
        model.Add(sum(indicators[value]) <= constraints["max_count"][value])
    
    # Schedule off days based on work patterns and leaves
    shift_preferences = inputs.get("shift_preferences", [])
    
    for i in range(config["no_employees"]):
        # Check if employee is on leave for current day
        employee_leaves = inputs.get("employee_leaves", [])
        if current_day is not None and i < len(employee_leaves):
            if current_day in employee_leaves[i]:
                # Employee is on leave - must be off
                model.Add(x[i] == 0)
                continue  # Skip work pattern check for leave days
        
        # Check work pattern off days
        pattern_id = inputs["work_pattern"][i]
        pattern = config["work_pattern"][pattern_id]
        shift_day = inputs["shift_day"][i]
        
        if shift_day % pattern["total_days"] in pattern["off_days"]:
            model.Add(x[i] == 0)
        else:
            model.Add(x[i] != 0)
        
        # Apply shift preferences: if employee has preferences, restrict to those shifts (or 0 for off)
        if i < len(shift_preferences) and shift_preferences[i]:
            # Employee can only work shifts from their preference list (or be off = 0)
            allowed_shifts = {0} | shift_preferences[i]  # Include 0 (off) and preferred shifts
            # Create constraint: x[i] must be in allowed_shifts
            # We do this by ensuring x[i] is NOT in the disallowed set
            disallowed_shifts = set(range(1, config["no_shifts"] + 1)) - shift_preferences[i]
            for disallowed_shift in disallowed_shifts:
                model.Add(x[i] != disallowed_shift)
    
    # Hard forbidden constraints: prevent certain shift sequences
    for k_val, forbidden_val in config["forbidden_constraints"]:
        for i in range(config["no_employees"]):
            if inputs["previous_day"][i] == k_val:
                model.Add(x[i] != forbidden_val)
    
    # Quality optimization: minimize variance in shift assignments (fairness)
    # Instead of exponential, use linear cost based on how many times employee has worked each shift
    # Lower quality_count means employee has worked that shift less = better
    total_quality = 0
    
    for i in range(config["no_employees"]):
        # Validate quality_count structure
        if len(inputs["quality_count"][i]) != config["no_shifts"]:
            raise ValueError(f"Employee {i} quality_count length ({len(inputs['quality_count'][i])}) doesn't match number of shifts ({config['no_shifts']})")
        
        # Calculate cost for each shift assignment for this employee
        # Cost is based on how many times they've already worked this shift
        shift_costs = []
        for shift in range(config["no_shifts"]):
            # FIXED BUG: Was using inputs["quality_count"][shift], should be [i][shift]
            quality_val = inputs["quality_count"][i][shift]
            
            # Use linear cost instead of exponential for better fairness
            # Lower quality_val (fewer times worked) = lower cost = better
            # Add 1 to avoid zero cost, and use quality_val directly
            cost = quality_val + 1
            shift_costs.append(cost)
        
        # Link shift assignment to quality cost
        for shift in range(config["no_shifts"]):
            shift_val = shift + 1  # Shift values are 1-indexed
            # Use existing indicator if available, otherwise create new
            if shift_val in indicators:
                total_quality += indicators[shift_val][i] * shift_costs[shift]
            else:
                # Fallback: create indicator if needed (shouldn't happen)
                shift_ind = model.NewBoolVar(f'quality_ind_{i}_{shift}')
                model.Add(x[i] == shift_val).OnlyEnforceIf(shift_ind)
                model.Add(x[i] != shift_val).OnlyEnforceIf(shift_ind.Not())
                total_quality += shift_ind * shift_costs[shift]
    
    # Minimize total quality (lower = more fair distribution)
    model.Minimize(total_quality)
    
    # Add constraints to avoid previously found solutions
    for prev_solution in prev_solutions:
        # At least one employee must have a different assignment
        or_conditions = []
        for i in range(config["no_employees"]):
            condition = model.NewBoolVar(f'diff_{i}_prev')
            model.Add(x[i] != prev_solution[i]).OnlyEnforceIf(condition)
            model.Add(x[i] == prev_solution[i]).OnlyEnforceIf(condition.Not())
            or_conditions.append(condition)
        
        # At least one difference required
        model.Add(sum(or_conditions) >= 1)
    
    # Solve the model
    solver = cp_model.CpSolver()
    
    # Improved search strategy
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH  # Better than FIXED_SEARCH
    solver.parameters.max_time_in_seconds = config.get("csp_time_limit", 30.0)  # Time limit per day
    solver.parameters.num_search_workers = 1  # Single-threaded for reproducibility
    
    # Solve
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        new_solution = [solver.Value(xi) for xi in x]
        
        # Compute new quality count (deep copy to avoid mutation)
        new_quality_count = copy.deepcopy(inputs["quality_count"])
        for i in range(config["no_employees"]):
            if new_solution[i] > 0:  # Only update for non-zero shifts
                shift_idx = new_solution[i] - 1
                new_quality_count[i][shift_idx] += 1
                
                # Normalize: subtract minimum to keep values bounded
                offset = min(new_quality_count[i])
                new_quality_count[i] = [
                    min(config.get("quality_threshold", 100), v - offset) 
                    for v in new_quality_count[i]
                ]
        
        return new_solution, new_quality_count
    else:
        return None, inputs["quality_count"]

# config = {
#     "no_employees": 30,
#     "no_shifts": 5,
#     "work_pattern": {
#         0: {"total_days": 7, "off_days": [5,6]},
#         1: {"total_days": 9, "off_days": [6,7,8]}
#     },
#     "forbidden_constraints": [(1,3), (2,4), (3,5)],
#     "quality_threshold": 5
# }
    
#     # Test inputs
# inputs = {
#     "shift_day": [i % 7 if i % 2 == 0 else i % 9 for i in range(30)],  # Example shift days
#     "work_pattern": [i % 2 for i in range(30)],  # Alternating work patterns
#     "previous_day": [i % 5 + 1 for i in range(30)],  # Alternating previous days
#     "quality_count": [[(i + j) % 5 for j in range(5)] for i in range(30)]  # Rotating quality counts for each employee
# }

# # Test constraints
# constraints = {
#     "min_count": {1: 4, 2: 4, 3: 4, 4: 4, 5: 4},
#     "max_count": {1: 8, 2: 8, 3: 8, 4: 8, 5: 8}
# }

# # Test the function
# solution, quality = create_day_schedule(config, inputs, constraints)

# print(solution)
# print(compute_quality_score(quality))
    
        

# def solve_csp(s, n, min_count, max_count, constants, forbidden_constraints, priority_lookup, shift_days, work_pattern, prev_solutions=None):
#     if prev_solutions is None:
#         prev_solutions = []

#     model = cp_model.CpModel()

#     # Define variables
#     x = [model.NewIntVar(0, n, f'x{i}') for i in range(s)]

#     # Define count constraints
#     for value in range(1, n + 1):
#         # Create indicator variables for x[i] == value
#         indicators = [model.NewBoolVar(f'indicator_{i}_{value}') for i in range(s)]
        
#         for i in range(s):
#             # Set the indicator variable to 1 if x[i] == value
#             model.Add(x[i] == value).OnlyEnforceIf(indicators[i])
#             model.Add(x[i] != value).OnlyEnforceIf(indicators[i].Not())
        
#         # Add the count constraint
#         model.Add(sum(indicators) >= min_count[value])
#         model.Add(sum(indicators) <= max_count[value])
    
#     for i in range(s):
#         if work_pattern[i] == 1:
#             if shift_days[i] % 7 in (5, 6):
#                 model.Add(x[i] == 0)
#             else:
#                 model.Add(x[i] != 0)
#         else:
#             if shift_days[i] % 9 in (6, 7, 8):
#                 model.Add(x[i] == 0)
#             else:
#                 model.Add(x[i] != 0)

#     # **Hard forbidden constraints**: Enforcing them directly as hard constraints
#     for k_val, forbidden_val in forbidden_constraints:
#         for i in range(s):
#             model.Add(x[i] != forbidden_val).OnlyEnforceIf(constants[i] == k_val)

#     # Add priority-based loose constraints and quality maximization
#     total_quality = 0  # Initialize the total quality score
    
#     for i in range(s):
#         # Lookup the allowed values and their priority order for constants[i]
#         allowed_values = priority_lookup[constants[i]]

#         # Create a list of indicator variables for each allowed value in the lookup
#         indicators = []
#         for idx, allowed_val in enumerate(allowed_values):
#             indicator = model.NewBoolVar(f'indicator_{i}_{allowed_val}')
#             indicators.append(indicator)

#             # Enforce x[i] == allowed_val and update the priority accordingly
#             model.Add(x[i] == allowed_val).OnlyEnforceIf(indicator)
        
#         # Add the total quality score as a linear combination of the priorities
#         quality_score = sum(indicator * (len(allowed_values) - idx) for idx, indicator in enumerate(indicators))
#         total_quality += quality_score

#     # Maximize the quality score
#     model.Maximize(total_quality)

#     # Solve the model
#     solver = cp_model.CpSolver()
    
#     # Set parameters to allow for finding multiple solutions
#     solver.parameters.search_branching = cp_model.FIXED_SEARCH  # Set search strategy
    
#     # Add constraints to avoid previously found solutions
#     for prev_solution in prev_solutions:
#     # Create a list to hold conditions for x[i] != prev_solution[i]
#         or_conditions = []
#         for i in range(s):
#             condition = model.NewBoolVar(f'or_condition_{i}_prev')
#             model.Add(x[i] != prev_solution[i]).OnlyEnforceIf(condition)
#             model.Add(x[i] == prev_solution[i]).OnlyEnforceIf(condition.Not())
#             or_conditions.append(condition)

#         # Ensure at least one of the conditions is true (OR logic)
#         model.Add(sum(or_conditions) >= 1)

#     # Solve the model and return the solution
#     status = solver.Solve(model)

#     if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
#         # Return the new solution that is different from the previous solutions
#         new_solution = [solver.Value(xi) for xi in x]
#         return new_solution
#     else:
#         return None
