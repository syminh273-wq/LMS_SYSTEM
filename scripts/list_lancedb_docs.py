import os
import django
import sys
import json
import lancedb

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

from django.conf import settings

def list_all_documents():
    db_path = os.path.join(settings.BASE_DIR, "lancedb")
    if not os.path.exists(db_path):
        print(f"LanceDB path does not exist: {db_path}")
        return

    db = lancedb.connect(db_path)
    table_names = db.table_names()
    
    if not table_names:
        print("No tables found in LanceDB.")
        return

    print(f"Found {len(table_names)} tables: {', '.join(table_names)}")
    print("-" * 50)

    for table_name in table_names:
        print(f"\nTable: {table_name}")
        tbl = db.open_table(table_name)
        
        # Using search().to_list() to get all data without needing pandas/pylance
        rows = tbl.search().to_list()
        
        if not rows:
            print("  (Table is empty)")
            continue

        print(f"  Total rows: {len(rows)}")
        
        # Display each row
        for row in rows:
            doc_id = row.get('id', 'N/A')
            content = row.get('document', '')
            meta_json = row.get('metadata_json', '{}')
            
            try:
                meta = json.loads(meta_json)
            except:
                meta = meta_json
            
            # Truncate content for display
            display_content = (content[:100] + '...') if len(content) > 100 else content
            
            print(f"\n  [ID]: {doc_id}")
            print(f"  [Content]: {display_content}")
            print(f"  [Metadata]: {json.dumps(meta, indent=2, ensure_ascii=False)}")
            print("  " + "." * 30)

if __name__ == "__main__":
    list_all_documents()
