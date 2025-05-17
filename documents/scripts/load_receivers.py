import pandas as pd
import os
import sys
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_tracker.settings')  # Adjust if needed
django.setup()

from documents.models import Staff, Division

# Load Excel with headers
file_path = 'list of receiver.xlsx'  # Update if stored elsewhere
df = pd.read_excel(file_path)

# ✅ Confirm expected column exists
if "Names" not in df.columns:
    raise ValueError("❌ 'Names' column not found in Excel.")

# ✅ Ensure default division exists
default_division, _ = Division.objects.get_or_create(name='Unassigned')

# 🧹 Delete all existing staff before reinserting
deleted_count, _ = Staff.objects.all().delete()
print(f"🧹 Deleted {deleted_count} existing staff records.")

# ✅ Insert receivers from 'Names' column
inserted_count = 0
for name in df["Names"]:
    if pd.notna(name):
        cleaned_name = str(name).strip()
        if cleaned_name and not cleaned_name.isnumeric():
            Staff.objects.create(name=cleaned_name, division=default_division)
            inserted_count += 1

print(f"✅ Successfully inserted {inserted_count} staff members.")
