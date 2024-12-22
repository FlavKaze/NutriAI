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
    
    
    
class GPTRH(BaseModel):
    explicacao_simplificada: str = Field(description="Explicação simplificada dos campos")
    explicacao_detalhada: str = Field(description="Explicação detalhada dos campos")
    sugestao_de_melhoria: str = Field(description="Sugestão de melhoria para melhorar os numeros")
 
if __name__ == '__main__':
    prompt = """
Voce é um especialista em Recursos Humanos e foi contratado para ajudar a 
    empresa a explicar os campos a baixo para o usuario do sistema de RH.

Com base no seu conhecimento e experiência, explique o que são os campos a baixo:

Mapa Estratégico

Metas Corporativas 60%
    Lucro operacional
    Volume de vendas

Metas Departamentais 80%
    Industrial
    Vendas

Metas Individuais 90%
    Mariza Cristina
    Airton Duarte
    
"""
    
    gpt = PydanticGPT(service_provider="openai", pydantic_object=GPTRH)
    print(gpt.inference([
        prompt,
    ])[0])

# {'explicacao_simplificada': 'Os campos referem-se a diferentes níveis de metas dentro de uma organização: estratégicas, corporativas, departamentais e individuais.', 'explicacao_detalhada': "O 'Mapa Estratégico' é uma ferramenta que ajuda a visualizar e comunicar a estratégia da empresa, mostrando como diferentes objetivos se conectam. 'Metas Corporativas 60%' refere-se a objetivos gerais da empresa, como 'Lucro operacional' e 'Volume de vendas', que têm um peso de 60% na avaliação geral. 'Metas Departamentais 80%' são objetivos específicos para cada departamento, como 'Industrial' e 'Vendas', com um peso de 80%. 'Metas Individuais 90%' são objetivos específicos para cada funcionário, como 'Mariza Cristina' e 'Airton Duarte', com um peso de 90%.", 'sugestao_de_melhoria': 'Para melhorar a compreensão, poderia-se incluir uma breve descrição de como cada meta contribui para o sucesso geral da empresa e exemplos de ações que podem ser tomadas para alcançá-las. Além disso, seria útil explicar como os pesos percentuais influenciam a avaliação de desempenho.'}
# {'explicacao_simplificada': 'O Mapa Estratégico é uma ferramenta que ajuda a empresa a alinhar suas atividades com sua visão e estratégia. As Metas Corporativas são objetivos gerais que a empresa quer alcançar, como aumentar o lucro operacional e o volume de vendas. As Metas Departamentais são objetivos específicos para cada departamento, como o setor Industrial e de Vendas. As Metas Individuais são objetivos específicos para cada funcionário, como Mariza Cristina e Airton Duarte.', 'explicacao_detalhada': 'O Mapa Estratégico é um diagrama que representa a estratégia da empresa, mostrando como diferentes objetivos e iniciativas estão interligados para alcançar a visão da organização. As Metas Corporativas, que têm um peso de 60%, são objetivos amplos que a empresa como um todo deve atingir, como aumentar o lucro operacional e o volume de vendas. As Metas Departamentais, com um peso de 80%, são objetivos específicos para cada departamento, como o setor Industrial e de Vendas, que contribuem para as metas corporativas. As Metas Individuais, com um peso de 90%, são objetivos específicos para cada colaborador, como Mariza Cristina e Airton Duarte, que devem ser alcançados para apoiar as metas departamentais e corporativas.', 'sugestao_de_melhoria': 'Para melhorar os números, a empresa pode considerar a implementação de um sistema de acompanhamento de metas mais robusto, que permita monitorar o progresso em tempo real e ajustar as estratégias conforme necessário. Além disso, promover treinamentos e workshops para os funcionários pode ajudar a alinhar todos com os objetivos estratégicos e aumentar o engajamento e a produtividade.'}