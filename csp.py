from ortools.sat.python import cp_model
import math

# def compute_quality_score(quality_count):
#     return sum(sum(math.exp(v) for v in row_val) for row_val in quality_count)


def create_day_schedule(config, inputs, constraints, prev_solutions=None):
    # s = no of employees
    # n = no of shifts
    
    if prev_solutions is None:
        prev_solutions = []
    
    model = cp_model.CpModel()
    
    # Initialise the variables
    x = [model.NewIntVar(0, config["no_shifts"], f'x{i}') for i in range(config["no_employees"])]
    
    for value in range(1, config["no_shifts"] + 1):
        # Create indicator boolean variables for x[i] == value
        indicators = [model.NewBoolVar(f'indicator_{i}_{value}') for i in range(config["no_employees"])]
        
        for i in range(config["no_employees"]):
            # Set the indicator variable to 1 if x[i] == value
            model.Add(x[i] == value).OnlyEnforceIf(indicators[i])
            model.Add(x[i] != value).OnlyEnforceIf(indicators[i].Not())
        
        # Add the count min and max constraint
        model.Add(sum(indicators) >= constraints["min_count"][value])
        model.Add(sum(indicators) <= constraints["max_count"][value])
        
    # Schedule off days
    for i in range(config["no_employees"]):
        if inputs["shift_day"][i] % config["work_pattern"][inputs["work_pattern"][i]]["total_days"] in config["work_pattern"][inputs["work_pattern"][i]]["off_days"]:
            model.Add(x[i] == 0)
        else:
            model.Add(x[i] != 0)
            
    # Hard forbidden constraints: Enforcing them directly as hard constraints
    for k_val, forbidden_val in config["forbidden_constraints"]:
        for i in range(config["no_employees"]):
            model.Add(x[i] != forbidden_val).OnlyEnforceIf(inputs["previous_day"][i] == k_val)
            
    # Quality maximization
    total_quality = 0
    
    # for i in range(config["no_employees"]):
        
    for i in range(config["no_employees"]):
        shift_indicators = [model.NewBoolVar(f'shift_ind_{i}_{shift}') for shift in range(config["no_shifts"])]
        shift_costs = []
        for shift in range(config["no_shifts"]):
            temp_list = [val + 1 for val in inputs["quality_count"][shift]]
            offset = min(temp_list)
            temp_list = [min(config["quality_threshold"], v - offset) for v in temp_list]
            shift_costs.append(sum(math.exp(v) for v in temp_list))
            model.Add(x[i] == shift + 1).OnlyEnforceIf(shift_indicators[shift])
            model.Add(x[i] != shift + 1).OnlyEnforceIf(shift_indicators[shift].Not())
        total_quality += sum(shift_indicators[shift] * shift_costs[shift] for shift in range(config["no_shifts"]))
    model.Maximize(total_quality)
    
    # Solve the model
    solver = cp_model.CpSolver()
    
    # Set parameters to allow for finding multiple solutions
    solver.parameters.search_branching = cp_model.FIXED_SEARCH  # Set search strategy
    
    # Add constraints to avoid previously found solutions
    for prev_solution in prev_solutions:
    # Create a list to hold conditions for x[i] != prev_solution[i]
        or_conditions = []
        for i in range(config["no_employees"]):
            condition = model.NewBoolVar(f'or_condition_{i}_prev')
            model.Add(x[i] != prev_solution[i]).OnlyEnforceIf(condition)
            model.Add(x[i] == prev_solution[i]).OnlyEnforceIf(condition.Not())
            or_conditions.append(condition)

        # Ensure at least one of the conditions is true (OR logic)
        model.Add(sum(or_conditions) >= 1)

    # Solve the model and return the solution
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Return the new solution that is different from the previous solutions
        new_solution = [solver.Value(xi) for xi in x]
        
        # Compute new quality count
        new_quality_count = inputs["quality_count"].copy()
        for i in range(config["no_employees"]):
            if new_solution[i] > 0:  # Only update for non-zero shifts
                new_quality_count[i][new_solution[i] - 1] += 1
                offset = min(new_quality_count[i])
                new_quality_count[i] = [min(config["quality_threshold"], v - offset) for v in new_quality_count[i]]
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
