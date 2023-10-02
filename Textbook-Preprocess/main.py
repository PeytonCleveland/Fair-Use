import shutil  # Needed for moving files
import re
import os
import logging
from tqdm import tqdm
from dotenv import load_dotenv
import openai
import shutil
import boto3


# ========================================================
# amazon adaptions
# ========================================================


s3 = boto3.client('s3', region_name='us-gov-west-1')

BUCKET_NAME = "ocelot-data-input"
IMPORT_SUBFOLDER = "Import"
EXPORT_SUBFOLDER = "Export"


def read_from_s3(file_key):
    """Reads a file from S3 given its key."""
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    content = obj['Body'].read().decode('utf-8')
    return content


def save_to_s3(data, file_key):
    """Writes data to an S3 file given its key."""
    s3.put_object(Body=data, Bucket=BUCKET_NAME, Key=file_key)


def list_files_in_s3_subfolder(subfolder_name):
    """Lists all files in a specific S3 subfolder."""
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=subfolder_name)
    return [item['Key'] for item in response.get('Contents', [])]


# ========================================================
# functions and main body
# ========================================================


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
openai_api_key = os.environ.get('OPENAI_API_KEY')
if not openai_api_key:
    logging.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not found in environment variables")
openai.api_key = openai_api_key


def read_all_textbooks(folder_path):
    textbooks = {}
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    title = file.replace('.txt', '')
                    content = f.read()
                    textbooks[title] = content
    return textbooks


def chunk_text(text, chunk_size=1500):
    # Split text by paragraphs
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []

    for paragraph in paragraphs:
        # Split paragraph by sentences
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        for sentence in sentences:
            current_chunk.append(sentence)

            # Check if adding the sentence exceeds the chunk_size
            if sum(len(word) for word in current_chunk) > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []

    # Add any remaining sentences to the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def get_context(previous_response):
    # Request a one-sentence summary from GPT-3.5-Turbo
    prompt = f"Summarize the following text in one sentence: {previous_response}"

    summary = get_response(prompt, context="", max_length=200)

    return summary


def get_response(chunk, context="", max_length=2500):
    system_prompt = f"""You are a technical writer simply transposing content from a textbook. Given the context: '{context}', your task is to 
    rewrite and improve the following content, ensuring you rewrite all its original meaning and technicality, paying attention to accuracy. If you notice missing information
    or errors, fill in the gaps or correct them. * it is critical however, that if the content appears to be a bibliography, introduction, copyright notice, gibberish,
    or other non-essential sections, replace it with '//*REMOVED*//'*. Here's the content:
    {chunk}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.8,
            max_tokens=max_length
        )
        return response.choices[0].message.content.strip()
    except openai.error.OpenAIError as e:
        logging.error(
            f"Error occurred while fetching response from OpenAI: {e}. Skipping this prompt.")
        return None


def save_to_file(filename, data):
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(data)


def save_checkpoint(title, chunk_index):
    with open("checkpoint.txt", 'w') as file:
        file.write(f"{title}\n{chunk_index}")


def load_checkpoint():
    if os.path.exists("checkpoint.txt"):
        with open("checkpoint.txt", 'r') as file:
            title = file.readline().strip()
            chunk_index = int(file.readline().strip())
            return title, chunk_index
    return None, None


# ========================================================
# main function
# ========================================================

if __name__ == "__main__":
    # Define the directory where the textbooks are stored
    import_directory_path = IMPORT_SUBFOLDER

    # Define a directory where the processed textbooks will be saved
    export_directory_path = EXPORT_SUBFOLDER
    if not os.path.exists(export_directory_path):
        # Create the directory if it doesn't exist
        os.makedirs(export_directory_path)

    # Read all textbooks
    textbook_files = list_files_in_s3_subfolder(import_directory_path)
    textbooks = {os.path.basename(file): read_from_s3(file)
                 for file in textbook_files}

    # load the checkpoint
    checkpoint_title, checkpoint_chunk_index = load_checkpoint()

    for title, content in tqdm(textbooks.items(), desc="Processing Textbooks", unit="book"):
        # If there's a checkpoint for the current title, start from the checkpointed chunk index
        if title == checkpoint_title:
            start_chunk_index = checkpoint_chunk_index
        else:
            start_chunk_index = 0

        output_filename = f"{title}.txt"
        chunks = chunk_text(content)

        with open(output_filename, "w", encoding='utf-8') as outfile:
            for index, chunk in enumerate(tqdm(chunks[start_chunk_index:], desc=f"Processing '{title[:20]}...'", leave=False, unit="chunk")):
                processed_output = get_response(chunk, context="")

                # Skip processing this chunk if the output matches the undesired pattern
                if processed_output == '//*REMOVED*//':
                    continue

                context = get_context(processed_output)

                # Only write output if it's not the undesired pattern
                outfile.write(f"Processed Chunk: {processed_output}\n")
                outfile.write(f"Context: {context}\n\n")

                # After processing each chunk, save the current progress as a checkpoint
                # +1 because it's zero-based indexing
                save_checkpoint(title, index + start_chunk_index + 1)

            outfile.write("==========\n\n")

        # After processing each textbook, move it to the export directory
        with open(output_filename, 'r', encoding='utf-8') as file:
            content = file.read()
        save_to_s3(content, os.path.join(
            export_directory_path, output_filename))

    # After processing all books, delete the checkpoint (if it exists)
    if os.path.exists("checkpoint.txt"):
        os.remove("checkpoint.txt")

    print("Processing completed.")
