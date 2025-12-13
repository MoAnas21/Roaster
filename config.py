# import json
# no_days = 30

# config = {
#     "no_employees": 30,
#     "no_shifts": 5,
#     "work_pattern": {
#         0: {"total_days": 7, "off_days": [5,6]},
#         1: {"total_days": 9, "off_days": [6,7,8]}
#     },
#     "forbidden_constraints": [(1,3), (2,4), (3,5)],
#     "quality_threshold": 100,
#     "threshold": 10,
# }

# inputs = {
#     "shift_day": [0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1],
#     "work_pattern": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
#     "previous_day": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
#     "quality_count": [
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3],
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3],
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3],
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3],
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3],
#         [0, 1, 2, 3, 4], [1, 2, 3, 4, 0], [2, 3, 4, 0, 1], [3, 4, 0, 1, 2], [4, 0, 1, 2, 3]
#     ]
# }

# constraints = {
#     "min_count": {1: 4, 2: 4, 3: 4, 4: 2, 5: 3},
#     "max_count": {1: 6, 2: 5, 3: 6, 4: 5, 5: 5}
# }

# # Print the results
# print("Config:")
# print(json.dumps(config, indent=2))
# print("\nInputs:")
# print(json.dumps(inputs, indent=2))
# print("\nConstraints:")
# print(json.dumps(constraints, indent=2))
# # Save the generated data to a JSON file
# output_data = {
#     "config": config,
#     "inputs": inputs,
#     "constraints": constraints
# }

# with open('original.json', 'w') as outfile:
#     json.dump(output_data, outfile, indent=2)

import json
import datetime

def generate_config_from_json(json_config):
    config = {
        "no_employees": json_config["no_of_employees"],
        "no_shifts": json_config["no_of_shifts"],
        "work_pattern": {},
        "forbidden_constraints": [],
        "quality_threshold": json_config.get("quality_threshold", 100),
        "threshold": json_config.get("threshold", 10),
    }
    
    for pattern in json_config["work_pattern"]:
        pattern_id = pattern["pettern_id"] - 1
        if "no_working_days" in pattern and "no_off_days" in pattern:
            total_days = pattern["no_working_days"] + pattern["no_off_days"]
            
            # Check if strict_weekend_off is enabled
            strict_weekend_off = False
            if "strict_weekend_off" in pattern:
                # Handle both string "True"/"False" and boolean
                strict_weekend_off = str(pattern["strict_weekend_off"]).lower() == "true" or pattern["strict_weekend_off"] is True
            
            if strict_weekend_off:
                # For strict_weekend_off, off days must be weekends (Saturday=5, Sunday=6)
                # In a 7-day week: Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
                # We need to ensure weekends are always off
                # For a 5 work + 2 off pattern, weekends should be off
                off_days = [5, 6]  # Saturday and Sunday
            else:
                # Normal pattern: off days at the end of the cycle
                off_days = list(range(total_days - pattern["no_off_days"], total_days))
            
            config["work_pattern"][pattern_id] = {
                "total_days": total_days,
                "off_days": off_days,
                "strict_weekend_off": strict_weekend_off
            }
    
    shifts_with_times = []
    for shift in json_config["shifts"]:
        start_time = datetime.datetime.combine(datetime.date.min, datetime.datetime.strptime(shift["start_time"], "%H:%M:%S").time())
        end_time = datetime.datetime.combine(datetime.date.min, datetime.datetime.strptime(shift["end_time"], "%H:%M:%S").time())
        if start_time >= end_time:
                end_time += datetime.timedelta(days=1)
        shifts_with_times.append({
            "shift_id": shift["shift_id"],
            "start_time": start_time,
            "end_time": end_time
        })
    
    config["all_shift_ids"] = [shift["shift_id"] for shift in json_config["shifts"]]
    
    for shift in shifts_with_times:
        for other_shift in shifts_with_times:
            if shift["shift_id"] != other_shift["shift_id"]:
                time_difference = other_shift['start_time'] + datetime.timedelta(days=1) - shift['end_time']
                if time_difference.total_seconds()//3600 < json_config['min_time_between_shifts']:
                    config["forbidden_constraints"].append((shift["shift_id"], other_shift["shift_id"]))

    employees = json_config["employees"]
    start_date_obj = datetime.datetime.strptime(json_config["start_date"], "%Y-%m-%d")
    end_date_obj = datetime.datetime.strptime(json_config["end_date"], "%Y-%m-%d")
    no_days = (end_date_obj - start_date_obj).days + 1
    
    inputs = {
        "shift_day": [],
        "work_pattern": [],
        "previous_day": [],
        "quality_count": [],
        "employee_leaves": [],  # List of sets, one per employee containing day indices when on leave
        "shift_preferences": []  # List of sets, one per employee containing preferred shift IDs (empty set = no preference)
    }

    for employee in employees:
        pattern_id = employee["preferred_work_pattern"] - 1
        pattern = config["work_pattern"].get(pattern_id, {})
        
        # Check if this pattern has strict_weekend_off
        if pattern.get("strict_weekend_off", False):
            # Recompute pattern position based on start_date to align with weekends
            # For strict_weekend_off, weekends (Saturday=5, Sunday=6) must be off days
            # Pattern cycle: 7 days (5 work + 2 off on weekends)
            # shift_day tracks position in pattern: 0-4 = work days, 5-6 = off days (weekends)
            
            # Find what day of week the start_date is (Monday=0, Sunday=6)
            start_weekday = start_date_obj.weekday()  # Monday=0, Sunday=6
            
            # For strict_weekend_off pattern:
            # - Monday (0) -> shift_day = 0 (first work day)
            # - Tuesday (1) -> shift_day = 1 (second work day)
            # - ...
            # - Friday (4) -> shift_day = 4 (fifth work day)
            # - Saturday (5) -> shift_day = 5 (first off day)
            # - Sunday (6) -> shift_day = 6 (second off day)
            
            # shift_day directly corresponds to weekday for strict_weekend_off
            initial_shift_day = start_weekday
            
            # Calculate no_work_days and no_off_days from initial_shift_day
            if initial_shift_day < 5:  # Monday-Friday (work days)
                no_work_days = initial_shift_day  # Days into work week
                no_off_days = 0  # Not in weekend yet
            elif initial_shift_day == 5:  # Saturday (first off day)
                no_work_days = 5  # Completed all 5 work days
                no_off_days = 0   # Starting first off day
            else:  # initial_shift_day == 6, Sunday (second off day)
                no_work_days = 5  # Completed all 5 work days
                no_off_days = 1   # On second off day
            
            # Update employee's pattern position
            employee["no_work_days_from_previous_pattern"] = no_work_days
            employee["no_off_days_from_previous_pattern"] = no_off_days
        
        # Use the (possibly recomputed) pattern position
        inputs["shift_day"].append(employee["no_work_days_from_previous_pattern"] + employee["no_off_days_from_previous_pattern"])
        inputs["work_pattern"].append(pattern_id)
        inputs["previous_day"].append(employee["last_shift"])
        inputs["quality_count"].append(employee["quality"])
        
        # Process leaves: convert date ranges to day indices (0-based from start_date)
        leave_days = set()
        if "leaves" in employee and employee["leaves"]:
            for leave in employee["leaves"]:
                leave_start = datetime.datetime.strptime(leave["start_date"], "%Y-%m-%d")
                leave_end = datetime.datetime.strptime(leave["end_date"], "%Y-%m-%d")
                
                # Calculate day indices (0-based from start_date)
                start_day_idx = (leave_start - start_date_obj).days
                end_day_idx = (leave_end - start_date_obj).days
                
                # Add all days in the leave range (inclusive)
                for day_idx in range(start_day_idx, end_day_idx + 1):
                    if 0 <= day_idx < no_days:  # Ensure within schedule range
                        leave_days.add(day_idx)
        
        inputs["employee_leaves"].append(leave_days)
        
        # Process shift preferences: if employee has shift_preference, restrict to those shifts
        if "shift_preference" in employee and employee["shift_preference"]:
            # Convert to set of shift IDs
            preferred_shifts = set(employee["shift_preference"])
            inputs["shift_preferences"].append(preferred_shifts)
        else:
            # No preference = can work any shift (empty set means no restriction)
            inputs["shift_preferences"].append(set())
    
    constraints = {
        "min_count": {},
        "max_count": {}
    }
    
    for shift in json_config["shifts"]:
        constraints["min_count"][shift["shift_id"]] = shift["min_no_of_employees"]
        constraints["max_count"][shift["shift_id"]] = shift["max_no_of_employees"]
    
    return no_days, config, inputs, constraints, employees

with open('config.json', 'r') as f:
    json_config = json.load(f)

start_date = datetime.datetime.strptime(json_config["start_date"], "%Y-%m-%d")
end_date = datetime.datetime.strptime(json_config["end_date"], "%Y-%m-%d")
no_days, config, inputs, constraints, employees = generate_config_from_json(json_config)
shift_colours = {"Off": "D3D3D3"} | {f"Shift {shift['shift_id']}": shift["colour"] for shift in json_config["shifts"]}

# print("Config:")
# print(json.dumps(config, indent=2))
# print("\nInputs:")
# print(json.dumps(inputs, indent=2))
# print("\nConstraints:")
# print(json.dumps(constraints, indent=2))

# output_data = {
#     "config": config,
#     "inputs": inputs,
#     "constraints": constraints
# }

# with open('converted.json', 'w') as outfile:
#     json.dump(output_data, outfile, indent=2)