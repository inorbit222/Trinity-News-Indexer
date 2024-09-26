import os
import re
import chardet  # Used for detecting encoding

# Define directories
input_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 1"  # Input directory for raw text files
output_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 2"  # Output directory for segmented text files

# Ensure the output directory exists; if not, create it
if not os.path.exists(output_directory):
    os.makedirs(output_directory)  # Create output directory if it doesn't exist

# Function to detect file encoding
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()  # Read binary data to detect encoding
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        return encoding

# Function to process a single file: reads the file, processes the text, and writes the result to a new file
def process_file(file_path, output_path):
    # Detect encoding of the file before reading it
    encoding = detect_encoding(file_path)
    
    # Open the input file with detected encoding and read its contents
    with open(file_path, 'r', encoding=encoding) as file:
        newspaper_text = file.read()  # Read the entire file as a single string

    # Define a regular expression pattern to identify titles and their corresponding bodies
    title_body_pattern = re.compile(r'([A-Z\s,\'\.]+)(?:\n|\n\n)(.+?)(?=\n[A-Z\s,\'\.]+\n|\n\n|\Z)', re.DOTALL)

    # Open the output file to write the processed data
    with open(output_path, 'w', encoding='utf-8') as output_file:
        # Loop through all matches found in the input file based on the regular expression pattern
        for match in title_body_pattern.finditer(newspaper_text):
            # Capture the title and body from the matched text
            title = match.group(1)  # Group 1: the title (in all caps)
            body = match.group(2)   # Group 2: the body of the article

            # Write the formatted article into the output file
            output_file.write(f"====================================\n")  # Add a separator before each article
            output_file.write(f"Title: {title}\n")  # Write the title
            output_file.write(f"Body:\n{body}\n")   # Write the body
            output_file.write(f"====================================\n\n")  # Add a separator after each article

    # Print a message to indicate that the file has been successfully processed and saved
    print(f"Preprocessing complete. Output saved to {output_path}")

# Iterate over all files in the input directory
for filename in os.listdir(input_directory):  # Loop through all the files in the input directory
    # Only process files that end with ".txt"
    if filename.lower().endswith(".txt"):
        # Construct full file paths for the input and output files
        input_file_path = os.path.join(input_directory, filename)  # Full path of the input file
        output_file_path = os.path.join(output_directory, filename.replace("seg1", "seg2"))  # Full path of the output file with "seg1" replaced by "seg2"
        
        # Process the file and save the output
        process_file(input_file_path, output_file_path)  # Call the process_file function for each file
