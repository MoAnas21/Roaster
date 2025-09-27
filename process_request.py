from config import config, inputs, constraints, no_days
from generate_roaster import simulate_roaster
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill

inputs["schedule"] = []
print("Starting simulation...")
print("no_days:", no_days)
print("config:", config)
print("inputs:", inputs)
print("constraints:", constraints)
final_solutions, final_quality_count = simulate_roaster(0, no_days, config, inputs, constraints)

if final_solutions is not None:
    added_final_solution = [inputs["previous_day"]] + final_solutions
    data = {}
    for i, day in enumerate(added_final_solution):
        column_name = f"Day {i + 1}"
        data[column_name] = [f"Shift {val}" if val != 0 else "Off" for val in day]

    data["Employee name"] = [f"Employee {j}" for j in range(1, len(added_final_solution[0]) + 1)]

    columns = ["Employee name"] + [f"Day {i}" for i in range(1, len(added_final_solution) + 1)]
    df = pd.DataFrame(data, columns=columns)
    df.to_csv("roaster.csv", index=False)

    wb = Workbook()
    ws = wb.active
    ws.title = "Roaster"

    # Move "Employee name" to the last column
    columns = [col for col in columns if col != "Employee name"] + ["Employee name"]

    for col_num, column_title in enumerate(columns, start=1):
        ws.cell(row=1, column=col_num, value=column_title)

    for row_num, employee_data in enumerate(zip(*[data[col] for col in columns]), start=2):
        for col_num, cell_value in enumerate(employee_data, start=1):
            ws.cell(row=row_num, column=col_num, value=cell_value)

    employee_name_color = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
    value_colors = {}
    color_palette = ["FFCCCC", "CCFFCC", "CCCCFF", "FFFFCC", "FFCCFF", "CCFFFF", "FFE5CC", "E5FFCC"]
    color_index = 0

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            if cell.column == ws.max_column:  # Last column (Employee name)
                cell.fill = employee_name_color
            else:
                if cell.value not in value_colors:
                    value_colors[cell.value] = PatternFill(start_color=color_palette[color_index % len(color_palette)],
                                                           end_color=color_palette[color_index % len(color_palette)],
                                                           fill_type="solid")
                    color_index += 1
                cell.fill = value_colors[cell.value]

    # Move "Employee name" to the first column
    columns = ["Employee name"] + [col for col in columns if col != "Employee name"]

    for col_num, column_title in enumerate(columns, start=1):
        ws.cell(row=1, column=col_num, value=column_title)

    for row_num, employee_data in enumerate(zip(*[data[col] for col in columns]), start=2):
        for col_num, cell_value in enumerate(employee_data, start=1):
            cell = ws.cell(row=row_num, column=col_num, value=cell_value)
            if col_num == 1:  # First column (Employee name)
                cell.fill = employee_name_color
            else:
                cell.fill = value_colors.get(cell_value, PatternFill(fill_type=None))
    wb.save("roaster.xlsx")