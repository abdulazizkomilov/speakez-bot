import os
import json
import random
import logging
import aiofiles

IELTS_QUESTIONS = "questions/speaking"
MULTILEVEL_QUESTIONS = "questions/multilevel"

async def get_random_question(part: int, category: str, mode_type: str):
    """Returns a random question and its corresponding audio_base64 asynchronously."""

    try:
        if not isinstance(part, int) or part not in {1, 2, 3}:
            return {"error": "Invalid part number. Please choose 1, 2, or 3."}

        if mode_type.lower() == "ielts":
            base_dir = IELTS_QUESTIONS
        elif mode_type.lower() == "multilevel":
            base_dir = MULTILEVEL_QUESTIONS
        else:
            return {"error": f"Invalid mode type '{mode_type}'. Must be 'ielts' or 'multilevel'."}

        category_path = os.path.join(base_dir, f"part_{part}", category)

        if not os.path.exists(category_path) or not os.path.isdir(category_path):
            return {"error": f"Category '{category}' not found in part {part} for mode '{mode_type}'."}

        question_files = [f for f in os.listdir(category_path) if f.endswith(".json")]

        if not question_files:
            return {"error": f"No questions found in category '{category}' for part {part} in mode '{mode_type}'."}

        random_file = random.choice(question_files)
        file_path = os.path.join(category_path, random_file)

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                question_data = json.loads(await f.read())
                return {
                    "question": question_data.get("question", "Unknown question"),
                    "audio_base64": question_data.get("audio_base64", None),
                }
        except (json.JSONDecodeError, FileNotFoundError):
            return {"error": f"Error reading file '{random_file}' in category '{category}'."}

    except Exception as e:
        logging.error(f"Error in get_random_question: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}
