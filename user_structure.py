import re
import pytz
from typing import List
from datetime import datetime
from unidecode import unidecode
from contextlib import suppress
from dataclasses import dataclass, asdict, field

import nltk
import dacite
import pandas as pd
from word2number import w2n
from fuzzywuzzy import process, fuzz

from gpt_langchain import PydanticGPT, GPTFood
from database import set_food_session, get_food_session

gpt = PydanticGPT(service_provider="google", pydantic_object=GPTFood, response_type=list)
conversation_gpt = PydanticGPT(service_provider="google")

nltk.download('stopwords')
fuso_horario = pytz.timezone('America/Sao_Paulo')

stopwords = nltk.corpus.stopwords.words('portuguese')
table_scale = 100
unit_words = {
    'g': 1,
    'grama': 1,
    'gramas': 1,
    'kg': 1000,
    'quilograma': 1000,
    'quilo': 1000,
    'kilo': 1000,
    'litro': 1000,
    'litros': 1000,
    'l': 1000,
    'ml': 1,
    'mililitro': 1,
    'mililitros': 1,
    'unidade': 1,
    'unidades': 1
}

def get_date():
    return datetime.now(fuso_horario).strftime('%Y-%m-%d')

@dataclass
class Food():
    name: str
    number: int = 0
    group: str = field(default="")
    quantity: float = 100
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    
    def __str__(self):
        """Format bealtifully the food values"""
        beatiful_str = f"{self.quantity}g/ml de {self.name}:\n"
        beatiful_str += f" - {self.kcal:.2f} kcal\n"
        beatiful_str += f" - {self.protein:.2f}g de proteína\n"
        beatiful_str += f" - {self.carbs:.2f}g de carboidratos\n"
        beatiful_str += f" - {self.fat:.2f}g de gorduras\n"
        beatiful_str += f" - {self.fiber:.2f}g de fibras\n"
        return beatiful_str

    def normalize_quantity(self):
        """Normalize the quantity of food to grams"""
        for food in ['kcal', 'protein', 'carbs', 'fat', 'fiber']:
            try:
                setattr(self, food, float(getattr(self, food)) * (self.quantity / table_scale))
            except ValueError:
                setattr(self, food, 0)


@dataclass
class DailyDiet():
    date: str
    foods: List[Food] = field(default_factory=list)
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    
    def __str__(self):
        """Format bealtifully the daily diet values"""
        beatiful_str = f"Dieta do dia {self.date}:\n"
        for food in self.foods:
            beatiful_str += str(food) + "\n"
        beatiful_str += f"Total:\n"
        beatiful_str += f" - {self.kcal:.2f} kcal\n"
        beatiful_str += f" - {self.protein:.2f}g de proteína\n"
        beatiful_str += f" - {self.carbs:.2f}g de carboidratos\n"
        beatiful_str += f" - {self.fat:.2f}g de gorduras\n"
        beatiful_str += f" - {self.fiber:.2f}g de fibras\n"
        return beatiful_str

@dataclass
class User():
    user_id: int
    name: str
    gender: str = ""
    objective: str = ""
    activity_level: str = ""
    daily_kcal: float = 0
    daily_carbs: float = 0
    daily_protein: float = 0
    daily_fat: float = 0
    daily_fiber: float = 0
    age: int = 0
    weight: float = 0
    height: float = 0
    all_diet: List[DailyDiet] = field(default_factory=list)
    
    def __str__(self):
        """Format bealtifully the user values"""
        beatiful_str = f"Objetivo: {self.objective}\n"
        beatiful_str = f"Usuário: {self.name}\n"
        beatiful_str = f"Gênero: {self.gender}\n"
        beatiful_str += f"Idade: {self.age}\n"
        beatiful_str += f"Peso: {self.weight}\n"
        beatiful_str += f"Altura: {self.height}\n"
        
        beatiful_str += f"Dieta:\n"
        for diet in self.all_diet:
            beatiful_str += str(diet) + "\n"
        return beatiful_str
    
    def get_daily_values(self):
        beatiful_str = f"Metas diárias:\n"
        beatiful_str += f"kcal: {self.daily_kcal:.2f}\n"
        beatiful_str += f"Proteínas: {self.daily_protein:.2f}\n"
        beatiful_str += f"Carboidratos: {self.daily_carbs:.2f}\n"
        beatiful_str += f"Gorduras: {self.daily_fat:.2f}\n"
        beatiful_str += f"Fibras: {self.daily_fiber:.2f}\n"
        return beatiful_str
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data):
        return dacite.from_dict(data_class=User, data=data)
        
    def create_diet(self,):
        date = get_date()
        diet = DailyDiet(date=date, foods=[], kcal=0, protein=0, carbs=0)
        if not self.all_diet:
            self.all_diet = []
        self.all_diet.append(diet)
        
    def get_last_diet(self):
        return self.all_diet[-1]
    
    def get_today_diet(self):
        return next((diet for diet in self.all_diet if diet.date == get_date()), None)
    
    def update_last_diet(self, foods: List[Food]):
        if not foods:
            return
        if not self.all_diet or self.all_diet[-1].date != get_date():
            self.create_diet()
        self.all_diet[-1].foods.extend(foods)
        for food in foods:
            self.all_diet[-1].kcal += food.kcal
            self.all_diet[-1].protein += food.protein
            self.all_diet[-1].carbs += food.carbs
            self.all_diet[-1].fat += food.fat
            self.all_diet[-1].fiber += food.fiber
    
    
def calcular_calorias_diarias(peso, altura, idade, sexo, nivel_atividade, objetivo):
    # peso = user.wheigh
    # altura = user.length
    # idade = user.age
    # sexo = user.gender
    # nivel_atividade = user.activity_level
    # objetivo = user.objective
    
    if sexo == 'Masculino':
        calorias_base = (10 * peso) + (6.25 * altura) - (5 * idade) + 5
    else:
        calorias_base = (10 * peso) + (6.25 * altura) - (5 * idade) - 161
    
    if nivel_atividade == "1": #'sedentario'
        calorias_base *= 1.2
    elif nivel_atividade == "2": #'levemente ativo'
        calorias_base *= 1.375
    elif nivel_atividade == "3": #'moderadamente ativo'
        calorias_base *= 1.55
    elif nivel_atividade == "4": #'muito ativo'
        calorias_base *= 1.725
    elif nivel_atividade == "5": #'extra ativo'
        calorias_base *= 1.9

    if objetivo == 'Perder peso':
        calorias_base *= 0.85  # Reduz 15% para déficit calórico
    elif objetivo == 'Ganhar peso':
        calorias_base *= 1.15  # Aumenta 15% para superávit calórico
    elif objetivo == 'Manter peso':
        pass

    return calorias_base

def calcular_macronutrientes(calorias, sexo):
    carboidratos = calorias * 0.50 / 4  # 50% das calorias, 4 calorias por grama
    proteinas = calorias * 0.20 / 4     # 20% das calorias, 4 calorias por grama
    gorduras = calorias * 0.30 / 9      # 30% das calorias, 9 calorias por grama
    fibras = 38 if sexo == 'Masculino' else 25  # Recomendações gerais de fibras
    return carboidratos, proteinas, gorduras, fibras


def split_text(text: str):
    """
    split food quantities/grams and names
    ex: 
     - 5 bananas
     - 1 apple
     - 100g of banana
     - 200g of apple
    """
    #first separate numbers and letters that are stuck together ex: 100g
    new_text = ""
    with suppress(ValueError):
        text = str(w2n.word_to_num(text))
        
    for i, letter in enumerate(text):
        if letter.isdigit() and text[i+1].isalpha():
            new_text += f"{letter} "
        else:
            new_text += letter
            
    #split text into groups composed sequence numbers and letters cut in numbers ignore spaces
    pares = re.findall(r'(\d+)\s*(.*?)\s*(?=\d|$)', new_text)
    food_list = [f"{num} de {item.strip()}" for num, item in pares]
    
    food_quantities = []
    food_names = []
    
    for text in food_list:
        current_number = ""
        current_word = ""
        for word in text.split():
            if word.lower() not in stopwords:
                if word.isdigit():
                    current_number += word
                elif word in unit_words:
                    current_number = f"{current_number} {word}"
                else:
                    current_word += f"{word} "
        food_quantities.append(current_number)
        food_names.append(unidecode(current_word.strip().lower()))
        
    return food_quantities, food_names


def find_food_in_df(text: str, df):
    # find exact match
    food = df[df['nome_do_alimento'].str.lower() == text.lower()]
    if not food.empty:
        return food.iloc[0].to_dict()
    #find food with fuzzy process
    food = process.extractOne(text, df['nome_do_alimento'], scorer=fuzz.token_sort_ratio)
    if food:
        return df[df['nome_do_alimento'] == food[0]].iloc[0].to_dict()


def normalize_quantity(quantity: str):
    """
    Normalize the quantity of food to grams
    """
    split_quantity = quantity.split()
    if len(split_quantity) == 1:
        return float(split_quantity[0])
    else:
        return float(split_quantity[0]) * unit_words[split_quantity[1]]
    

def create_food_from_text(text: str = None, df: pd.DataFrame = None, food_list: List[dict] = None):
    if not df.empty:
        food_quantities, food_names = split_text(text)
        normalized_quantities = [normalize_quantity(quantity) for quantity in food_quantities]
        foods = []
        for food_name, quantity in zip(food_names, normalized_quantities):
        
            food = find_food_in_df(food_name, df)
            if not food:
                continue
            obj_food = Food(
                name=food['nome_do_alimento'],
                number=food['id'],
                group=food['categoria'],
                quantity=quantity,
                kcal=str(food['calorias']).replace(",", "."),
                protein=str(food['proteinas']).replace(",", "."),
                carbs=str(food['carboidratos']).replace(",", "."),
                fat=str(food['gorduras']).replace(",", "."),
                fiber=str(food['fibras']).replace(",", ".")
            )
            obj_food.normalize_quantity()
            foods.append(obj_food)
    elif food_list:
        for food in food_list:
            obj_food = Food(
                name=food['nome_do_alimento'],
                number=-1,
                group="LLM",
                quantity=food['quantity'],
                kcal=food['calorias'],
                protein=food['proteinas'],
                carbs=food['carboidratos'],
                fat=food['gorduras'],
                fiber=food['fibras']
            )
            obj_food.normalize_quantity()
            foods.append(obj_food)
            
        foods = [Food(**food) for food in food_list]
    return foods

def conversation_with_gpt(text: str):
    prompt = """
    Você é um especialista em nutrição, que irá conversar com o usuario.
    ele te enviou uma msg, responda como um profissional de saúde que é uma coruja.
    as respostas vão para um app de msg, entao seja claro e objetivo.
    utilize poucas palavras pois ningume gosta de textao nas menssagens.
    
    macros nutrientes dos alimentos vao ser adicionados após sua msg entao não responda sobre isso.
    {question}
    """
    return conversation_gpt.inference([prompt.format(question=text)])[0]


def create_food_from_gpt(text: str):
    prompt = """
Voce é um especialista em nutrição, que irá me ajudar a descobrir os macronutrientes dos alimentos.

    - Ultilizando a tabela TACO e a tabela de composição de alimentos da USP
    - Se for necessário, utilize outras fontes confiáveis
    
Seguindo as regras a cima, me responda:
    {question}
"""
    
    food_quantities, food_names = split_text(text)
    normalized_quantities = [normalize_quantity(quantity) for quantity in food_quantities]
    foods_text  = ""
    gpt_quantities = []
    gpt_foods = []
    foods = []
    for idx, food_name in enumerate(food_names):
        current_food = get_food_session(food_name)
        if current_food:
            current_food.quantity = normalized_quantities[idx]
            current_food.normalize_quantity()
            foods.append(current_food)
            continue
        foods_text += "- Quantas calorias tem em {quantity}g de {name}?\n".format(quantity=100, name=food_name)
        gpt_quantities.append(normalized_quantities[idx])
        gpt_foods.append(food_name)
        
    if foods_text:
        food_list = gpt.inference([prompt.format(question=foods_text)])[0]
        for food, quantity, food_name in zip(food_list, gpt_quantities, gpt_foods):
            obj_food = Food(
                name=food_name,
                number=-1,
                group="LLM",
                quantity=quantity,
                kcal=food['kcal'],
                protein=food['protein'],
                carbs=food['carbs'],
                fat=food['fat'],
                fiber=food['fiber']
            )
            set_food_session(food_name, obj_food)
            obj_food.normalize_quantity()
            foods.append(obj_food)
    return foods

if __name__ == '__main__':
    # import pandas as pd
    # df = pd.read_csv("data/Tacotable.csv")
    # text = "200g de banana nanica"
    # foods = create_food_from_text(text, df)
    # print(foods)
    # user = User(user_id="123", name="John")
    # user.create_diet()
    # user.update_last_diet(foods)
    # print(user.get_last_diet())
    # print(user.to_dict())
    
    print(create_food_from_gpt("200g de banana nanica e 350g de peito de frango frito"))
    print()
    

    