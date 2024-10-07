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

# Function to process a single file: takes a raw text file and segments it into articles
def process_file(file_path, output_path):
    # Detect the file encoding
    encoding = detect_file_encoding(file_path)
    print(f"[INFO] Detected encoding for {file_path}: {encoding}")

    # Open the input file using the detected encoding, with error handling
    with open(file_path, 'r', encoding=encoding, errors='replace') as file:
        newspaper_text = file.read()  # Read the entire file as a single string

    # Define a regular expression pattern to identify article titles and their corresponding bodies
    article_pattern = re.compile(r'(?<=\n\n)([^\n]{1,80})\n+([^\n]+\n(.+\n)*)')

    # Find all matches in the text (i.e., articles) and store them in a list
    matches = list(article_pattern.finditer(newspaper_text))

    # Open the output file to write the segmented articles
    with open(output_path, 'w', encoding='utf-8') as output_file:
        last_pos = 0  # This variable tracks the position of the last processed article

        # Loop through all matches (i.e., each found article)
        for match in matches:
            # Capture the title and body of the current article
            title = match.group(1)  # Title of the article
            body = match.group(2)   # Body of the article

            # Write everything before the current article (uncategorized text or header information)
            output_file.write(newspaper_text[last_pos:match.start()])

            # Write the article in a structured format
            output_file.write(f"====================================\n")  # Article delimiter
            output_file.write(f"Title: {title}\n")  # Write the title of the article
            output_file.write(f"Body:\n{body}\n")   # Write the body of the article
            output_file.write(f"====================================\n\n")  # End of article delimiter

            # Update the last position to the end of the current article, ensuring the next loop iteration picks up after this article
            last_pos = match.end()

        # After the last match, write any remaining text (uncategorized text or footer) to the output file
        output_file.write(newspaper_text[last_pos:])

    # Log that the file has been successfully processed and saved
    print(f"Processed articles and uncategorized text saved to {output_path}")

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
