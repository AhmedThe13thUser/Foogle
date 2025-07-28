import json

def merge_json_files(file1_path, file2_path, output_path):
    """
    Merge two JSON files into one output file.
    
    Args:
        file1_path (str): Path to first JSON file
        file2_path (str): Path to second JSON file
        output_path (str): Path to output merged JSON file
    """
    try:
        # Load data from first file
        with open(file1_path, 'r') as file1:
            data1 = json.load(file1)
        
        # Load data from second file
        with open(file2_path, 'r') as file2:
            data2 = json.load(file2)
        
        # Merge the data
        # Assuming both files contain lists that should be concatenated
        if isinstance(data1, list) and isinstance(data2, list):
            merged_data = data1 + data2
        elif isinstance(data1, dict) and isinstance(data2, dict):
            merged_data = {**data1, **data2}  # Merge dictionaries
        else:
            # If types don't match or are unexpected, create a list with both
            merged_data = [data1, data2]
        
        # Save merged data to output file
        with open(output_path, 'w') as output_file:
            json.dump(merged_data, output_file, indent=2)
        
        print(f"Successfully merged files into {output_path}")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# File paths
file1 = 'indexing-1.json'
file2 = 'indexing-2.json'
output_file = 'indexing.json'

# Merge the files
merge_json_files(file1, file2, output_file)