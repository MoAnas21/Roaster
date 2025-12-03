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
            
            off_days = list(range(total_days - pattern["no_off_days"], total_days))
            
            config["work_pattern"][pattern_id] = {
                "total_days": total_days,
                "off_days": off_days
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
    no_days = (datetime.datetime.strptime(json_config["end_date"], "%Y-%m-%d") - 
               datetime.datetime.strptime(json_config["start_date"], "%Y-%m-%d")).days + 1
    
    inputs = {
        "shift_day": [],
        "work_pattern": [],
        "previous_day": [],
        "quality_count": []
    }

    for employee in employees:
        inputs["shift_day"].append(employee["no_work_days_from_previous_pattern"] + employee["no_off_days_from_previous_pattern"])
        inputs["work_pattern"].append(employee["preferred_work_pattern"] - 1)
        inputs["previous_day"].append(employee["last_shift"])
        inputs["quality_count"].append(employee["quality"])
    
    constraints = {
        "min_count": {},
        "max_count": {}
    }
    
    for shift in json_config["shifts"]:
        constraints["min_count"][shift["shift_id"]] = shift["min_no_of_employees"]
        constraints["max_count"][shift["shift_id"]] = shift["max_no_of_employees"]
    
    return no_days, config, inputs, constraints, employees

with open('code/config.json', 'r') as f:
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