# Base question generation
EQUAL_PROMPT = "Generate a level 1 JavaScript question on the topic of {topic} with an answer."

# System prompts for various purposes
SYSTEM_PROMPTS = {
    "question": "Given the topic {topic}, create a JavaScript question.",
    "answer": "What's the detailed answer to the JavaScript question: {question}?",
    "explanation": "Provide an detailed explanation for the answer to the JavaScript question: {question}.",
}

# Depth evolution
DEPTH_EVOLUTION_PROMPTS = [
    "Evolve this JavaScript question to next level {next_level} question: {question}.",
    "How can we make the JavaScript question \"{question}\" more challenging?"
]

# Difficulty assessment
DIFFICULTY_PROMPT = "On a scale of 1 to 10, how difficult is this JavaScript question: {question}? Provide a rating."

# Breadth evolution (in case we decide to incorporate this feature in the future)
BREADTH_EVOLUTION_PROMPT = [
    "Generate a new and different type of JavaScript question on the same topic as: {question}.",
    "Provide an alternative angle or approach to ask a JavaScript question related to: {question}."
]
