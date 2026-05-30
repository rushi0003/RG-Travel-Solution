"""
Quick script to remove unreachable driver code from admin_dashboard.dart
"""

file_path = r"c:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_flutter\lib\screens\admin\admin_dashboard.dart"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Delete lines 1188-2349 (0-indexed: 1187-2348)
# Keep lines 0-1187 and 2349-end
new_lines = lines[:1187] + lines[2349:]

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Removed {2349 - 1187} lines of unreachable driver code")
print(f"Old line count: {len(lines)}")
print(f"New line count: {len(new_lines)}")
print("File updated successfully!")
