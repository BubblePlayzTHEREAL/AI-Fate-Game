import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    LLAMA_TOPIC_IP = os.environ.get('LLAMA_TOPIC_IP', 'http://localhost:11434')
    LLAMA_JUDGE_IP = os.environ.get('LLAMA_JUDGE_IP', 'http://localhost:11434')
    MAX_ROUNDS = int(os.environ.get('MAX_ROUNDS', '5'))
