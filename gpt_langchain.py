import warnings
from typing import List, Dict, Any

import tiktoken
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI



from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import OutputFixingParser
from langchain.output_parsers import PydanticOutputParser

import config


class PydanticGPT:
    def __init__(
            self, service_provider: str = 'azure',
            gpt_model_name: str = config.OPENAI_MODEL_NAME,
            max_tokens: int = None, response_type: Any = None,
            pydantic_object: BaseModel = None, 
            temperature: float = config.GPT_TEMPERATURE
        ) -> None:
        self.service_provider = service_provider
        self.gpt_model_name = gpt_model_name
        self.chat_model = None
        self.prompt = None
        self.temperature = temperature
        self.max_tokens = max_tokens or config.OPENAI_MAX_TOKENS - 100 - 280 # model tokens - response size - prompt size
        self.encoding = tiktoken.encoding_for_model(gpt_model_name)
        self.response_type = response_type
        self.pydantic_object = pydantic_object
        self._start_gpt_caller()

    def create_gpt_response(self) -> List[Dict]:
        """Create a GPT response schema based on a pydantic object."""
        if self.response_type == list and self.pydantic_object:
            self.response_type = List[self.pydantic_object]
        elif self.response_type is None and self.pydantic_object:
            self.response_type = self.pydantic_object
        else:
            self.response_type = str

        class Response(BaseModel):
            response: self.response_type

        return Response

    def _start_gpt_caller(self) -> None:
        """Start model and create schemas for request and GPT response."""

        if self.service_provider == 'openai':
            self.chat_model = ChatOpenAI(
                model_name=self.gpt_model_name, 
                openai_api_key=config.OPENAI_API_KEY, 
                temperature=self.temperature,
                request_timeout=config.GPT_REQUEST_TIMEOUT,
                max_retries=config.GPT_MAX_RETRIES,  
            )
        elif self.service_provider == 'azure':
            self.chat_model = AzureChatOpenAI(
                api_key=config.AZURE_GPT4_API_KEY,
                openai_api_version=config.AZURE_GPT4_API_VERSION,
                azure_endpoint=config.AZURE_GPT4_ENDPOINT,
                azure_deployment=config.AZURE_GPT4_CHAT_DEPLOYMENT_NAME,
                temperature=self.temperature,
                request_timeout=config.GPT_REQUEST_TIMEOUT,
                max_retries=config.GPT_MAX_RETRIES,
            )
        elif self.service_provider == 'google':
            self.chat_model = ChatGoogleGenerativeAI(
                model=config.GOOGLE_API_MODEL,
                api_key=config.GOOGLE_API_KEY,
                temperature=self.temperature,
                request_timeout=config.GPT_REQUEST_TIMEOUT,
                max_retries=config.GPT_MAX_RETRIES,
            )
        else:
            raise ValueError("Service provider not found")
        
        pydantic_object = self.create_gpt_response()
        self.parser = PydanticOutputParser(pydantic_object=pydantic_object)
        self.new_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.chat_model)

        self.prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{text}\n",
            input_variables=["text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

    
    def crop(self, text: str) -> str:
        """ Crops the text based on the OpenAI tokenizer """
        tokens = self.encoding.encode(text)
        if len(tokens) >= self.max_tokens:
            text = self.encoding.decode(tokens[:self.max_tokens])
        return text

    def make_prompt(self, text):
        """Prepare the prompt to be sent to ChatGPT."""
        return self.prompt.format_prompt(
            text=text,
        )

    def inference(self, texts: list):
        """
        Perform ChatGPT-based text generation and inference texts.

        Args:
            texts (list of str): A list of input texts for which you want to 
                generate responses.

        Returns:
            list of dict: A list of JSON-formatted responses generated 
                by the chat model for each input text.
        """
        outputs = []
        for text in texts:
            try:
                _input = self.make_prompt(self.crop(text=text))
                output = self.chat_model.invoke(_input.to_messages())
                try:
                    json_out = self.parser.parse(output.content)
                except Exception as e:
                    json_out = self.new_parser.parse(output.content)

                outputs.append(json_out.dict().get("response"))
            except Exception as e:
                msg = f'ChatGPT error!! - Error{e}'
                warnings.warn(msg, Warning)
                break
        return outputs

class GPTFood(BaseModel):
    name: str = Field(decription="Food name")
    quantity: float = Field(description="Food quantity in grams")
    kcal: float = Field(description="Food calories")
    protein: float = Field(description="Food protein")
    carbs: float = Field(description="Food carbohydrates")
    fat: float = Field(description="Food fat")
    fiber: float = Field(description="Food fiber")
    
    
if __name__ == '__main__':
    prompt = """
Voce é um especialista em nutrição, que irá me ajudar a descobrir os macronutrientes dos alimentos.

    - Ultilizando a tabela TACO e a tabela de composição de alimentos da USP
    - Se for necessário, utilize outras fontes confiáveis
    
Seguindo as regras a cima, me responda:
    Quantas calorias tem em {quantity}g de {name}?
"""
    
    gpt = PydanticGPT(service_provider="google", pydantic_object=Food)
    print(gpt.inference([
        prompt.format(name="ovo cozido", quantity=100),
    ])[0])
