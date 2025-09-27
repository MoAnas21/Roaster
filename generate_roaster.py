from csp import create_day_schedule
    
def simulate_roaster(day_no, total_no_days, config, inputs, constraints):
    if day_no == total_no_days:
        return inputs["schedule"], inputs["quality_count"]
    solutions = []
    print(f"\nIteration {day_no + 1}:")
    while True:
        solution, quality_count = create_day_schedule(config, inputs, constraints, solutions)
        if solution is None:
            return None, None
        else: 
            solutions.append(solution)
            inputs["schedule"].append(solution)
            if(len(solutions) == config["threshold"]):
                return None, None
            new_input = inputs.copy()
            new_input["shift_day"] = [val + 1 for val in inputs["shift_day"]]
            new_input["quality_count"] = quality_count
            new_input["previous_day"] = solution
            new_input["schedule"] = inputs["schedule"].copy()
            added_schedule, final_quality_count = simulate_roaster(day_no + 1, total_no_days, config, new_input, constraints)
            if added_schedule is not None:
                return added_schedule, final_quality_count
            else:
                inputs["schedule"].pop()