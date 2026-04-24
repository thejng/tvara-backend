#DATASET CLEANING

import json
import re

def clean_train_data(input_file_path, output_file_path):
    """
    Reads a malformed JSON file, cleans extraneous single quotes
    from keys and string values, and saves a valid JSON file.
    """
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        # Step 1: Clean the outer keys like "'00851'" -> '"00851"'
      
        cleaned_content = re.sub(r"\"'(\d+)'\":", r'"\1":', raw_content)

        # Step 2: Parse the partially cleaned JSON
        data = json.loads(cleaned_content)

        # Step 3: Recursively clean internal values like "'01:10:00'" -> "01:10:00"
        def recursive_clean(obj):
            if isinstance(obj, dict):
                return {k: recursive_clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursive_clean(elem) for elem in obj]
            elif isinstance(obj, str):
                # Remove single quotes if they are at the start and end of a string
                if obj.startswith("'") and obj.endswith("'"):
                    return obj[1:-1]
            return obj

        cleaned_data = recursive_clean(data)

        # Step 4: Save the fully cleaned data and use it
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2)

        print(f"✅ Successfully cleaned data and saved to {output_file_path}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

# --- Usage ---
# Assuming your data is in a file named 'train_data.json'
clean_train_data('trainDetails.json', 'train_data_cleaned.json')
