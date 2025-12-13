import datetime
import pandas as pd

def validate_config(config):
    required_keys = {
        'start_date', 'end_date', 
        'no_work_pattern', 'work_pattern',
        'no_of_shifts', 'shifts', "min_time_between_shifts",
        'no_of_employees', 'employees',
    } #TODO: Check for any more required mandatory keys
    
    ############################# Required keys #############################
    if not required_keys.issubset(config.keys()):
        raise ValueError(f'Config must contain {required_keys}')
    
    
    ############################# Start date and end date #############################
    try: 
        config['start_date'] = pd.to_datetime(config["start_date"])
        config['end_date'] = pd.to_datetime(config["end_date"])
    except:
        raise ValueError('Start date and end date must be in the format YYYY-MM-DD')
    if config['start_date'] > config['end_date']:
        raise ValueError('Start date must be before end date')
    config["no_days"] = (config['end_date'] - config['start_date']).days + 1
    
    
    ############################# Shifts #############################
    if not isinstance(config['no_of_shifts'], int):
        raise ValueError('Number of shifts must be an integer')
    if not isinstance(config['shifts'], list):
        raise ValueError('Shifts must be a list')
    if not isinstance(config['min_time_between_shifts'], int):
        raise ValueError('Minimum time between shifts must be an integer')
    if len(config['shifts']) != config['no_of_shifts']:
        raise ValueError('Number of shifts must match the length of shifts list')
    
    for shift in config['shifts']:
        if not isinstance(shift, dict):
            raise ValueError('Each shift must be a dictionary')
        required_keys_shifts = {'shift_id', 'start_time', 'end_time', 'min_no_of_employees', 'max_no_of_employees'}
        if not required_keys_shifts.issubset(shift.keys()):
            raise ValueError(f'Each shift must contain the keys: {required_keys_shifts}')
        try:
            shift['start_time'] = datetime.datetime.combine(datetime.date.min, pd.to_datetime(shift['start_time']).time())
            shift['end_time'] = datetime.datetime.combine(datetime.date.min, pd.to_datetime(shift['end_time']).time())
            if shift['start_time'] >= shift['end_time']:
                shift['end_time'] += datetime.timedelta(days=1)
        except:
            raise ValueError('Start time and end time must be in the format HH:MM:SS')
        if not (isinstance(shift['min_no_of_employees'], int) and isinstance(shift['max_no_of_employees'], int)):
            raise ValueError('Number of employees in shift must be integers')
        if not (shift['min_no_of_employees'] <= shift['max_no_of_employees']):
            raise ValueError('Number of employees in shift must satisfy min <= max')
    
    config["all_shift_ids"] = [shift['shift_id'] for shift in config['shifts']]
    config["Unacceptable_shift_patterns"] = []
    for shift in config['shifts']:
        for other_shift in config['shifts']:
            if shift['shift_id'] != other_shift['shift_id']:
                time_difference = other_shift['start_time'] + datetime.timedelta(days=1) - shift['end_time']
                if time_difference.total_seconds()//3600 < config['min_time_between_shifts']:
                    config["Unacceptable_shift_patterns"].append((shift['shift_id'], other_shift['shift_id']))
          
    ############################# Work pattern #############################
    if not isinstance(config['no_work_pattern'], int):
        raise ValueError('No work pattern must be an integer')
    if not isinstance(config['work_pattern'], list):
        raise ValueError('Work pattern must be a list')
    if len(config['work_pattern']) != config['no_work_pattern']:
        raise ValueError('Number of shifts must match the length of work pattern list')
    for work_pattern in config['work_pattern']:
        if not isinstance(work_pattern, dict):
            raise ValueError('Each work pattern must be a dictionary')
        required_keys_work_pattern = {'pettern_id', 'no_working_days', 'no_off_days'}
        if not required_keys_work_pattern.issubset(work_pattern.keys()):
            raise ValueError(f'Each work pattern must contain the keys: {required_keys_work_pattern}')
        if not isinstance(work_pattern['work_pattern_id'], int):
            raise ValueError('Work pattern id must be an integer')
        if not isinstance(work_pattern['no_working_days'], int):
            raise ValueError('Number of working days must be an integer')
        if not isinstance(work_pattern['no_off_days'], int):
            raise ValueError('Number of off days must be an integer')
        # Validate strict_weekend_off
        if "strict_weekend_off" in work_pattern:
            strict_weekend_off_val = work_pattern["strict_weekend_off"]
            # Handle both string "True"/"False" and boolean
            if isinstance(strict_weekend_off_val, str):
                if strict_weekend_off_val.lower() not in ["true", "false"]:
                    raise ValueError(f'Work pattern {work_pattern.get("pettern_id", "unknown")}: strict_weekend_off must be "True", "False", or boolean')
            elif not isinstance(strict_weekend_off_val, bool):
                raise ValueError(f'Work pattern {work_pattern.get("pettern_id", "unknown")}: strict_weekend_off must be "True", "False", or boolean')
            
            strict_weekend_off = str(strict_weekend_off_val).lower() == "true" or strict_weekend_off_val is True
            
            # Validate that strict_weekend_off makes sense
            if strict_weekend_off:
                # For strict_weekend_off, off_days should be 2 (weekends)
                if work_pattern["no_off_days"] != 2:
                    raise ValueError(
                        f'Work pattern {work_pattern.get("pettern_id", "unknown")}: strict_weekend_off=True requires '
                        f'no_off_days=2 (for weekends), but got no_off_days={work_pattern["no_off_days"]}'
                    )
                # Total days should be 7 (5 work + 2 off)
                total_days = work_pattern["no_working_days"] + work_pattern["no_off_days"]
                if total_days != 7:
                    raise ValueError(
                        f'Work pattern {work_pattern.get("pettern_id", "unknown")}: strict_weekend_off=True requires '
                        f'total_days=7 (5 work + 2 off), but got total_days={total_days}'
                    )
        else:
            work_pattern["strict_weekend_off"] = False
        
        if "same_shift_in_pattern" not in work_pattern.keys():
            work_pattern["same_shift_in_pattern"] = False
        if "shifts" not in config.keys():
            work_pattern["shifts"] = config["all_shift_ids"]      
    
    ############################# Employees #############################
    if not isinstance(config['no_of_employees'], int):
        raise ValueError('Number of employees must be an integer')
    if not isinstance(config['employees'], list):
        raise ValueError('Employees must be a list')
    # if len(config['employees']) != config['no_of_employees']:
    #     raise ValueError('Number of employees must match the length of employees list')
    
    # Validate employee leaves
    schedule_start = config['start_date']
    schedule_end = config['end_date']
    
    for emp_idx, employee in enumerate(config['employees']):
        if not isinstance(employee, dict):
            raise ValueError(f'Employee at index {emp_idx} must be a dictionary')
        
        # Validate leaves if present
        if 'leaves' in employee:
            leaves = employee['leaves']
            if not isinstance(leaves, list):
                raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): "leaves" must be a list')
            
            for leave_idx, leave in enumerate(leaves):
                if not isinstance(leave, dict):
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): Leave {leave_idx} must be a dictionary')
                
                required_leave_keys = {'start_date', 'end_date'}
                if not required_leave_keys.issubset(leave.keys()):
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): Leave {leave_idx} must contain keys: {required_leave_keys}')
                
                # Validate date formats
                try:
                    leave_start = pd.to_datetime(leave['start_date'])
                    leave_end = pd.to_datetime(leave['end_date'])
                except:
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): Leave {leave_idx} dates must be in format YYYY-MM-DD')
                
                # Validate date order
                if leave_start > leave_end:
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): Leave {leave_idx} start_date ({leave["start_date"]}) must be before or equal to end_date ({leave["end_date"]})')
                
                # Validate leave is within schedule range
                if leave_start < schedule_start or leave_end > schedule_end:
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): Leave {leave_idx} ({leave["start_date"]} to {leave["end_date"]}) is outside schedule range ({schedule_start.strftime("%Y-%m-%d")} to {schedule_end.strftime("%Y-%m-%d")})')
        
        # Validate shift preferences if present
        if 'shift_preference' in employee:
            shift_pref = employee['shift_preference']
            if not isinstance(shift_pref, list):
                raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): "shift_preference" must be a list')
            
            if len(shift_pref) == 0:
                raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): "shift_preference" cannot be empty (use no field for no preference)')
            
            # Get valid shift IDs
            valid_shift_ids = config.get("all_shift_ids", [])
            if not valid_shift_ids:
                # Fallback: generate from no_of_shifts
                valid_shift_ids = list(range(1, config.get("no_of_shifts", 0) + 1))
            
            for pref_idx, shift_id in enumerate(shift_pref):
                if not isinstance(shift_id, int):
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): shift_preference[{pref_idx}] must be an integer')
                if shift_id not in valid_shift_ids:
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): shift_preference[{pref_idx}] = {shift_id} is not a valid shift ID. Valid IDs: {valid_shift_ids}')
        
        # Validate shift exclusions if present
        if 'shift_exclusion' in employee:
            shift_excl = employee['shift_exclusion']
            if not isinstance(shift_excl, list):
                raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): "shift_exclusion" must be a list')
            
            if len(shift_excl) == 0:
                raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): "shift_exclusion" cannot be empty (use no field for no exclusions)')
            
            # Get valid shift IDs
            valid_shift_ids = config.get("all_shift_ids", [])
            if not valid_shift_ids:
                # Fallback: generate from no_of_shifts
                valid_shift_ids = list(range(1, config.get("no_of_shifts", 0) + 1))
            
            for excl_idx, shift_id in enumerate(shift_excl):
                if not isinstance(shift_id, int):
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): shift_exclusion[{excl_idx}] must be an integer')
                if shift_id not in valid_shift_ids:
                    raise ValueError(f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): shift_exclusion[{excl_idx}] = {shift_id} is not a valid shift ID. Valid IDs: {valid_shift_ids}')
            
            # Check for conflicts: employee cannot have both preference and exclusion for same shift
            if 'shift_preference' in employee and employee['shift_preference']:
                conflicting_shifts = set(shift_excl) & set(employee['shift_preference'])
                if conflicting_shifts:
                    raise ValueError(
                        f'Employee {emp_idx} (ID: {employee.get("employee_id", "unknown")}): '
                        f'shift_exclusion and shift_preference cannot overlap. Conflicting shifts: {sorted(conflicting_shifts)}'
                    )
    
    return config