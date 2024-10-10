import os
import re
import configparser
import chardet
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Define directories
output_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 1"  # Directory to store the segmented output files

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')
input_directory = config['directories']['input_directory']

# Ensure the output directory exists; if not, create it
if not os.path.exists(output_directory):
    os.makedirs(output_directory)  # Create the directory if it doesn't exist

# Function to detect encoding of a file
def detect_file_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']

# Cleaning function to remove unwanted characters but keep newlines intact
def clean_text_with_newlines(text):
    """
    Clean the text by removing unwanted characters but keep newlines intact.
    """
    # Remove non-alphabetic characters except common punctuation (retain: . , ! ? ' ", newlines)
    text = re.sub(r'[^\w.,!?\'"\s\n-]', '', text)
    
    # Handle hyphenated words (join lines ending with '-')
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

    # Replace multiple spaces/tabs with a single space, but keep newlines intact
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Strip leading/trailing whitespace from lines
    text = '\n'.join(line.strip() for line in text.splitlines())

    return text

# Function to process a single file: takes a raw text file and segments it into articles
import re

# Adjusted function to process the file and handle poetry sections.
# Function to process the file and handle articles, poetry, and advertisements
def process_file(file_path, output_path):
    # Detect the file encoding
    encoding = detect_file_encoding(file_path)
    print(f"[INFO] Detected encoding for {file_path}: {encoding}")

    # Open the input file using the detected encoding, with error handling
    with open(file_path, 'r', encoding=encoding, errors='replace') as file:
        newspaper_text = file.read()  # Read the entire file as a single string

    # Define a regular expression pattern to identify standard articles
    
    # Define a regular expression pattern to identify article titles and their corresponding bodies
# The title should be 3 or more characters, and avoid titles that are just punctuation.
        article_pattern = re.compile(r'(?<=\n\n)([^\n]{1,80})\n+([^\n]+\n(.+\n)*)')
        poetry_pattern = re.compile(r'(Selected Poetry|BY [A-Z\s]+)\n+([^\n]+\n(.+\n)*)')


    # Define a pattern for identifying advertisement sections (adjust this to match your ad structure)
    ad_pattern = re.compile(r'([A-Z\s]+(?:CO|CO\.|INC|LTD|ADVERTISEMENT|SALE|NOTICE|WHOLESALE))\n+([^\n]+\n(.+\n)*)')  # Pattern for ads (company names)

    # Find all matches in the text for articles, poetry, and ads
    article_matches = list(article_pattern.finditer(newspaper_text))
    poetry_matches = list(poetry_pattern.finditer(newspaper_text))
    ad_matches = list(ad_pattern.finditer(newspaper_text))

    # Open the output file to write the segmented articles
    with open(output_path, 'w', encoding='utf-8') as output_file:
        last_pos = 0  # This variable tracks the position of the last processed article

        # Process articles
        for match in article_matches:
            title = match.group(1)
            body = match.group(2)

            output_file.write(newspaper_text[last_pos:match.start()])  # Write uncategorized text before the article
            output_file.write(f"====================================\n")
            output_file.write(f"Title: {title}\n")
            output_file.write(f"Body:\n{body}\n")
            output_file.write(f"====================================\n\n")
            last_pos = match.end()

        # Process poetry
        for poetry_match in poetry_matches:
            poetry_title = poetry_match.group(1)
            poetry_body = poetry_match.group(2)

            output_file.write(f"====================================\n")
            output_file.write(f"Poetry Title: {poetry_title}\n")
            output_file.write(f"Body:\n{poetry_body}\n")
            output_file.write(f"====================================\n\n")
            last_pos = poetry_match.end()

        # Process advertisements
        for ad_match in ad_matches:
    # Check if the match has enough groups before accessing them
            if ad_match and len(ad_match.groups()) >= 2:
                ad_title = ad_match.group(1)
                ad_body = ad_match.group(2)

                output_file.write(f"====================================\n")
                output_file.write(f"Advertisement Title: {ad_title}\n")
                output_file.write(f"Body:\n{ad_body}\n")
                output_file.write(f"====================================\n\n")
                last_pos = ad_match.end()
        #else:
       #     print(f"[WARNING] Advertisement match does not contain enough groups: {ad_match}")

        # Write any remaining uncategorized text
        output_file.write(newspaper_text[last_pos:])

    # Log that the file has been successfully processed and saved
    print(f"Processed articles, poetry, and advertisements saved to {output_path}")



# Iterate over all files in the input directory
def process_all_files():
    for filename in os.listdir(input_directory):
        # Only process files that end with ".txt"
        if filename.lower().endswith(".txt"):
            # Construct full paths for both the input and output files
            input_file_path = os.path.join(input_directory, filename)  # Full path to the input file
            output_file_path = os.path.join(output_directory, filename.replace(".txt", "_seg1.txt"))  # Output file with "_seg1" suffix
            
            # Process the file and save the output
            process_file(input_file_path, output_file_path)  # Call the process_file function on each .txt file

# Main function
if __name__ == "__main__":
    process_all_files()
