import PIL.Image
import google.generativeai as genai

import config

# decoretor for retrying the request
def retry_request(func):
    def wrapper(*args, **kwargs):
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Error: {e}")
                print(f"Retrying request {i+1}")
        return None
    return wrapper

class LLMInference:
    def __init__(self, model_temperature: float = config.MODEL_TEMPERATURE):
        self.api_key = config.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model_basic = genai.GenerativeModel('gemini-1.0-pro-latest')
        self.model_vision = genai.GenerativeModel('gemini-1.0-pro-vision-latest')
        self.model_chat = genai.GenerativeModel('gemini-1.0-pro-latest')
        self.chat = None
        self.generation_config = genai.types.GenerationConfig(
            # candidate_count=1,
            # stop_sequences=['x'],
            # max_output_tokens=20,
            temperature=model_temperature
    )
        
    @retry_request
    def generate_content(self, text: str) -> str:
        response = self.model_basic.generate_content(text)
        return response.text
    
    @retry_request
    def generate_content_vision(self, text: str, img: PIL.Image) -> str:
        response = self.model_vision.generate_content(
            [text, img],
            # stream=True,
            generation_config=self.generation_config
        )
        # response.resolve()
        return response.text
    
    @retry_request
    def chat_content(self, text: str) -> str:
        if self.chat is None:
            self.chat = self.model_chat.start_chat(history=[])
        response = self.chat.send_message(text)
        return response.text

    