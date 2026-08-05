from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

def create_excel_report(report_data, fields, excel_path, empty_row_template, company_name):
    wb = Workbook()
    ws = wb.active
    ws.title = company_name

    CS_PALETTE = ["DDEBF7", "E2EFDA", "FFF2CC", "FCE4D6", "E6E6FA"] 
    VS_PALETTE = ["FFFFFF", "F2F2F2"]

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    center_alignment = Alignment(horizontal="center", vertical="center")
    
    thin_border = Border(left=Side(style='thin', color='BFBFBF'),
                         right=Side(style='thin', color='BFBFBF'),
                         top=Side(style='thin', color='BFBFBF'),
                         bottom=Side(style='thin', color='BFBFBF'))

    ws.append(fields)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border

    current_row = 2
    empty_rows_indices = []

    last_cs = None
    last_vs = None
    cs_idx = -1
    vs_idx = -1

    for row_data in report_data:
        if row_data == empty_row_template:
            empty_rows_indices.append(current_row)
            ws.append([""] * len(fields))
            for col_idx in range(1, len(fields) + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
            current_row += 1
            continue

        current_cs = row_data.get("Content Switch", "")
        current_vs = row_data.get("Load Balancer", "")

        if current_cs != last_cs:
            cs_idx += 1
            last_cs = current_cs
        
        if current_vs != last_vs:
            vs_idx += 1
            last_vs = current_vs

        cs_color = CS_PALETTE[cs_idx % len(CS_PALETTE)]
        vs_color = VS_PALETTE[vs_idx % len(VS_PALETTE)]

        cs_fill = PatternFill(start_color=cs_color, end_color=cs_color, fill_type="solid")
        vs_fill = PatternFill(start_color=vs_color, end_color=vs_color, fill_type="solid")

        row_list = [row_data.get(f, "") for f in fields]
        ws.append(row_list)
        
        for col_idx in range(1, len(fields) + 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.alignment = center_alignment
            cell.border = thin_border
            
            if col_idx <= 5:
                cell.fill = cs_fill
            else:
                cell.fill = vs_fill
                
        current_row += 1

    for row_idx in empty_rows_indices:
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=len(fields))

    last_row = ws.max_row

    start_cs_row = 2
    for row in range(2, last_row + 2):
        current_cs = ws.cell(row=row, column=1).value if row <= last_row else None
        prev_cs = ws.cell(row=start_cs_row, column=1).value
        
        if current_cs != prev_cs or row > last_row:
            if row - 1 > start_cs_row and prev_cs and prev_cs != "":
                for col_idx in range(1, 6): 
                    ws.merge_cells(start_row=start_cs_row, start_column=col_idx, end_row=row-1, end_column=col_idx)
            start_cs_row = row

    start_lb_row = 2
    for row in range(2, last_row + 2):
        current_lb = ws.cell(row=row, column=6).value if row <= last_row else None
        prev_lb = ws.cell(row=start_lb_row, column=6).value
        
        if current_lb != prev_lb or row > last_row:
            if row - 1 > start_lb_row and prev_lb and prev_lb != "":
                for col_idx in range(6, 9): 
                    ws.merge_cells(start_row=start_lb_row, start_column=col_idx, end_row=row-1, end_column=col_idx)
            start_lb_row = row

    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                val = str(cell.value) if cell.value is not None else ""
                if len(val) > max_length:
                    max_length = len(val)
            except:
                pass
        
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width

    wb.save(excel_path)