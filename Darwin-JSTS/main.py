import os
import logging
import csv
import argparse
from tqdm import tqdm
import sys
from dotenv import load_dotenv
import openai

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
openai_api_key = os.environ.get('OPENAI_API_KEY')
if not openai_api_key:
    logging.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not found in environment variables")
openai.api_key = openai_api_key


def get_response(prompt_text, max_length=256):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.8,
            max_tokens=max_length  # Setting the maximum tokens for the response
        )
        return response.choices[0].message.content.strip()
    except openai.error.OpenAIError as e:
        logging.error(
            f"Error occurred while fetching response from OpenAI: {e}. Skipping this prompt.")
        return None


def read_seed_topics(seed_file):
    topics = []
    with open(seed_file, 'r') as file:
        for line in file:
            topic = line.strip()
            for level in range(1, 11):  # Generate prompts for levels 1 to 10
                system_prompt = f"You are a JavaScript tutor from MIT trying to create LeetCode-style coding questions for your student. Create a understandable, readable, and approachable LeetCode-style coding question a topic related to '{topic}' and ask a level {level} question."
                topics.append((topic, level, system_prompt))
    return topics


def save_to_csv(filename, data, mode='w'):
    with open(filename, mode, newline='', encoding='utf-8') as file:
        fieldnames = ["Topic", "Question",
                      "Answer", "Difficulty", "Explanation"]
        if any('MultipleChoice' in row for row in data):
            fieldnames.append("MultipleChoice")
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        for row in data:
            if 'MultipleChoice' not in row:
                # Handle cases where it's not present
                row['MultipleChoice'] = ""
            writer.writerow({k: v for k, v in row.items() if k in fieldnames})


def generate_initial_questions(topics):
    initial_qa_pairs = []
    for topic, level, system_prompt in tqdm(topics, desc="Generating Initial Questions", ncols=100):
        # Generate a user prompt (question)
        question = get_response(
            f"Craft a level {level} JavaScript coding question related to '{topic}'.", max_length=256)

        # Use the system prompt to guide the assistant's response
        answer = get_response(system_prompt, max_length=256)

        # Generate a multiple-choice question
        multiple_choice_question = get_response(
            f"Create a multiple-choice question related to '{topic}' with 4 options.", max_length=256)

        # Specify that we want a concise yet insightful explanation.
        explanation = get_response(
            f"Provide a concise yet insightful explanation supporting the answer to the coding question: '{question}'", max_length=256)

        initial_qa_pairs.append({
            "Topic": topic,
            "Question": question,
            "Answer": answer,
            "Difficulty": level,
            "Explanation": explanation,
            "MultipleChoice": multiple_choice_question
        })
    return initial_qa_pairs


def evolve_questions(qa_pairs, epoch):
    evolved_pairs = []
    for qa in qa_pairs:
        if qa["Difficulty"] >= 10:
            evolved_pairs.append(qa)
            continue

        new_question = get_response(
            f"Evolve the JavaScript question '{qa['Question']}' to make it a level {qa['Difficulty'] + 1} question.")
        new_explanation = get_response(
            f"Provide a indepth explanation for the JavaScript question: {new_question}")

        evolved_pairs.append({
            "Topic": qa["Topic"],
            "Question": new_question,
            "Answer": qa["Answer"],
            "Difficulty": qa["Difficulty"] + 1,
            "Explanation": new_explanation
        })
    return evolved_pairs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate a set of JavaScript questions based on seed topics and evolve them over epochs.')
    parser.add_argument('seed_topics', type=str,
                        help='Input CSV file containing initial topics.')
    parser.add_argument('output_file', type=str,
                        help='Output CSV file to save the generated questions and answers.')
    parser.add_argument('--epochs', type=int, default=9,
                        help='Number of epochs to run the evolution process. Default is 9.')
    args = parser.parse_args()

    seed_topics = read_seed_topics(args.seed_topics)
    initial_qa_pairs = generate_initial_questions(seed_topics)
    save_to_csv(args.output_file, initial_qa_pairs)

    for epoch in tqdm(range(args.epochs), desc="Evolving Questions", ncols=100):
        evolved_qa_pairs = evolve_questions(initial_qa_pairs, epoch + 1)
        save_to_csv(args.output_file, evolved_qa_pairs, mode='a')

        # Update initial_qa_pairs with evolved questions for the next epoch
        initial_qa_pairs = evolved_qa_pairs.copy()
