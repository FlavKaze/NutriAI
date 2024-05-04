from user_structure import User, create_food_from_text
from database import get_user_session, set_user_session
import pandas as pd
import speech_recognition as sr
from pydub import AudioSegment
import os
from io import BytesIO
from matplotlib import pyplot as plt
import tempfile
import matplotlib.animation as animation
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from llm_model_inference import LLMInference
from bson import json_util

df = pd.read_csv("Tacotable.csv")
llm_model = LLMInference()

def send_image_to_llm(image: Image) -> str:
    """Send the image to the LLM model."""
    text = "Me diga todos os alimentos que estão na imagem."
    return llm_model.generate_content_vision(text, image)


def user_interaction_for_add_quantity(text):
    """Add the quantity to the text."""
    text = text.replace("\n", ", 100g ")
    return "100g " + text
    

def normalize_llm_text(text: str) -> str:
    """Normalize the text from the LLM model."""
    text = "".join([w for w in text if w.isalpha() or w in [" ", "\n"]]).strip()
    return text


def add_food_from_image(image: BytesIO, user_id):
    """Add food from image."""
    if get_user_session(user_id):
        user = User.from_dict(get_user_session(user_id))
    else:
        text = "Usuário não encontrado! Por favor, registre-se com o comando /register."
        return text
    
    food_text = send_image_to_llm(Image.open(image))
    try:
        food_text = normalize_llm_text(food_text)
        food_text = user_interaction_for_add_quantity(food_text)
        
        foods = create_food_from_text(text=food_text, df=df)
        if not foods:
            text = "Alimento não encontrado!"
            return text
        user.update_last_diet(foods)
        set_user_session(user_id, user.to_dict())
        food_str = '\n'.join([str(food) for food in foods])
        text_to_send = f"Alimentos adicionados com sucesso! \n\n {food_str}"
        return text_to_send
    
    except Exception as e:
        print(e)
        
    return "Alimento não encontrado!"
    


def add_food(user_text, user_id):
    if get_user_session(user_id):
        user = User.from_dict(get_user_session(user_id))
    else:
        text = "Usuário não encontrado! Por favor, registre-se com o comando /register."
        return text
        
                
    foods = create_food_from_text(user_text, df)
    if not foods:
        text = "Alimento não encontrado!"
        return text
    
    user.update_last_diet(foods)
    set_user_session(user_id, user.to_dict())
    food_str = '\n'.join([str(food) for food in foods])
    text_to_send = f"Alimentos adicionados com sucesso! \n\n {food_str}"
    return text_to_send

def delete_last_food(user_id):
    user = User.from_dict(get_user_session(user_id))
    last_diet = user.get_last_diet()
    if not last_diet or not last_diet.foods:
        return "Nenhum alimento encontrado!"
    
    last_diet.kcal -= last_diet.foods[-1].kcal
    last_diet.protein -= last_diet.foods[-1].protein
    last_diet.carbs -= last_diet.foods[-1].carbs
    last_diet.fat -= last_diet.foods[-1].fat
    last_diet.fiber -= last_diet.foods[-1].fiber
    last_diet.foods.pop()
    set_user_session(user_id, user.to_dict())
    return "Último alimento removido com sucesso!"

def prepare_voice_file(path: str = None, audio_bytes: BytesIO = None) -> str:
    """
    Converts the input audio file to WAV format if necessary and returns the path to the WAV file.
    """
    if path:
        if os.path.splitext(path)[1] == '.wav':
            return path
        elif os.path.splitext(path)[1] in ('.mp3', '.m4a', '.ogg', '.flac'):
            audio_file = AudioSegment.from_file(
                path, format=os.path.splitext(path)[1][1:])
            wav_file = os.path.splitext(path)[0] + '.wav'
            audio_file.export(wav_file, format='wav')
            return wav_file
    elif audio_bytes:
        audio_file = AudioSegment.from_file(audio_bytes, format='ogg')
        wav_file = BytesIO()
        audio_file.export(wav_file, format='wav')
        return wav_file
    else:
        raise ValueError(
            f'Unsupported audio format: {format(os.path.splitext(path)[1])}')
        

def transcribe_audio(audio_bytes: BytesIO) -> str:
    """Transcribe the input audio file to text."""
    r = sr.Recognizer()
    wav_file = prepare_voice_file(audio_bytes=audio_bytes)

    with sr.AudioFile(wav_file) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio, language='pt-BR')
        return text
    except sr.UnknownValueError:
        return "Não entendi o que você disse"

    
def generate_chart(label, meta, atual) -> None:
    _, ax = plt.subplots(figsize=(3, 3))
    color_labels = {
        'kcal': '#F1C40F',
        'protain': '#5DAD00',
        'carbs': '#F39C12',
        'fat': '#FF5733',
        'fiber': '#3498DB',
    }
    
    ax.pie([max(meta-atual, 0), atual],
        wedgeprops={'width':0.3}, 
        startangle=90, 
        colors=['#515A5A', color_labels[label]])

    percent = atual / meta * 100
    center_text = f'{label}\n{percent:.0f}%'.title()
    nomalized_fontsize = 40 * (1 / (1 + 0.1 * len(center_text)))
    ax.text(0, 0, center_text, color=color_labels[label], ha='center', va='center', fontsize=nomalized_fontsize)
    fig_bytes = BytesIO()
    plt.savefig(fig_bytes, dpi=300, bbox_inches='tight', pad_inches=0.5, transparent=False)
    return fig_bytes
    

def generate_gif(user: User):
    image_array = []
    labels = ['kcal', 'protain', 'carbs', 'fat', 'fiber']
    metas = [user.daily_kcal, user.daily_protein, user.daily_carbs, user.daily_fat, user.daily_fiber]
    atuais = [user.all_diet[-1].kcal, user.all_diet[-1].protein, user.all_diet[-1].carbs, user.all_diet[-1].fat, user.all_diet[-1].fiber]
    
    for label, meta, atual in zip(labels, metas, atuais):
        fig_bytes = generate_chart(label, meta, atual)
        fig_bytes.seek(0)
        image = Image.open(fig_bytes)
        image_array.append(image)

    # Create the figure and axes objects
    fig, ax = plt.subplots(figsize=(2, 2))

    # Set the initial image
    im = ax.imshow(image_array[0], animated=True)
    
    def update(i):  
        im.set_array(image_array[i])
        return im, 

    # remove grad from fig
    ax.axis('off')
    # Create the animation object
    animation_fig = animation.FuncAnimation(fig, update, frames=len(image_array), interval=3000, blit=True, repeat_delay=10)

    # Show the animation
    with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_file:
        writer = animation.PillowWriter(fps=0.5, metadata=dict(artist="FlavKaze"), bitrate=3000)
        animation_fig.save(temp_file.name, writer=writer, dpi=300)

        # Read the file contents into a BytesIO object
        temp_file.seek(0)
        buf = BytesIO(temp_file.read())
        buf.seek(0)
    return buf
    
    
if __name__ == "__main__":
    add_food_from_image(Image.open("/home/flaviogaspareto/documents/vscode/NutriAI/image.png"), 0)
