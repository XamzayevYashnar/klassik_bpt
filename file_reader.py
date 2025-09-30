import os
from config import FOLDER_PATH, PROCESSED_LOG

def get_processed_lines():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f.readlines())

def save_processed_lines(lines):
    with open(PROCESSED_LOG, 'a', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

def read_new_lines():
    processed = get_processed_lines()
    new_entries = []
    for file in os.listdir(FOLDER_PATH):
        if file.endswith(".txt"):
            with open(os.path.join(FOLDER_PATH, file), 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and line not in processed:
                        new_entries.append((file, line))
    return new_entries
