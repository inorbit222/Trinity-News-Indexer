import os
import re
import chardet

# Define directories
input_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 2"  # Directory containing the segmented 2 text files
output_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 3"  # Directory to save the output of segmented 3 files

# Ensure the output directory exists; if not, create it
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Function to detect encoding
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

# Function to process a single file: reads from input and writes processed data to output
def process_file(input_path, output_path):
    # Detect the encoding of the file
    encoding = detect_encoding(input_path)
    
    # Open the input file and read its lines using the detected encoding
    with open(input_path, 'r', encoding=encoding) as file:
        lines = file.readlines()

    # Initialize variables to hold the title and body of the current article being processed
    output = []
    current_title = None
    current_body = []
    processing_article = False  # Flag to check if we're inside an article section

    # Function to handle writing an article to the output
    def write_article():
        nonlocal current_title, current_body  # Allow access to variables defined outside this function
        current_title = current_title if current_title is not None else ""  # Ensure the title is not None

        # If the title is blank, extract the first five words from the body
        if current_title.strip() == "" and current_body:
            first_line_of_body = current_body[0].strip()  # Take the first line of the body

            # Extract the first five words from the body text
            first_five_words = ' '.join(first_line_of_body.split()[:5])  # Split into words and take the first five

            if first_five_words:
                current_title = first_five_words.strip()  # Set the title to these first five words
                # Optionally remove the extracted title from the body to avoid duplication
                current_body[0] = current_body[0].replace(current_title, "").strip()

        # Skip this article if both the title and body are empty
        if current_title.strip() == "" and len(current_body) == 1 and current_body[0].strip() == "Body:":
            return  # Do nothing if both title and body are empty

        # Also skip if the title and body combined result in empty content
        if current_title.strip() == "" and ''.join(current_body).strip() == "":
            return

        # If there is actual content, write the article in the desired format
        output.append("====================================")
        output.append(f"Title: {current_title.strip()}")
        output.append(f"Body: {''.join(current_body).strip()}")
        output.append("====================================\n")

    # Loop through each line of the input file
    for line in lines:
        # Start a new section when the delimiter "====================================" is found
        if "====================================" in line:
            if processing_article:
                write_article()  # Write the previous article before starting a new one
            processing_article = True  # We are now processing a new article
            current_title = None  # Reset the title for the new article
            current_body = []  # Reset the body for the new article

        # Extract the title from lines starting with "Title:"
        elif line.startswith("Title:"):
            current_title = line.replace("Title:", "").strip()  # Remove "Title:" and store the remaining text as title

        # Start collecting body content from lines starting with "Body:"
        elif line.startswith("Body:"):
            current_body = []  # Clear any previous body content to start fresh

        # Any other line is part of the body content
        else:
            current_body.append(line)

    # After looping through all lines, write the last article if it's present
    write_article()

    # Save the output to the specified output file
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write('\n'.join(output))  # Join all the processed lines and write them to the file

    print(f"Processing complete. Output saved to {output_path}")  # Notify that processing is done

# Iterate over all text files in the input directory
for filename in os.listdir(input_directory):
    if filename.lower().endswith(".txt"):  # Process only files that end with ".txt"
        input_file_path = os.path.join(input_directory, filename)  # Get the full path of the input file
        output_file_path = os.path.join(output_directory, filename.replace("seg2", "seg3"))  # Modify the filename for the output

        # Process the file and save the output
        process_file(input_file_path, output_file_path)
