import logging
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext, ConversationHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import InlineQueryHandler
from io import BytesIO
import requests


from user_structure import User, create_food_from_text
from database import get_user_session, set_user_session
from client_output import add_food, transcribe_audio, delete_last_food, generate_gif


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

commands = {
    "/register": "Registra um novo usuário",
    "/deletefood": "Remove o último alimento adicionado",
    "/today": "mostra a dieta de hoje.",
}
    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_send = "Olá! Bem vindo ao seu assistente de dieta! Para começar, registre-se com o comando /register"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Para ver os comandos disponíveis, use /help")
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_send = "Comandos disponíveis:\n"
    text_to_send += '\n'.join([f"{command}: {description}" for command, description in commands.items()])
    text_to_send += "\n\nPara adicionar alimentos à sua dieta, mande mensagens de voz ou texto. ex: '100g banana, 250g maçã'"
    text_to_send += "\n\n Lembre se de sempre informar a quantidade em gramas!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)

async def register_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    text_to_send = add_food(user_text, user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)
    
async def get_diet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if get_user_session(user_id):
        user = User.from_dict(get_user_session(user_id))
        last_diet = user.get_today_diet()
        if not last_diet:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Nenhuma dieta encontrada para hoje!")
            return

        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(last_diet))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=user.get_daily_values())
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Calculando macronutrientes...")
        temp_file = generate_gif(user)
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation=temp_file, filename='pie_chart.gif')



# async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = update.message.from_user.id
#     user_text = update.message.text

#     if get_user_session(user_id):
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="Usuário já existe!")
#     else:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, insira um nome:")
        
#     return 1

       
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    if not user_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, insira um nome válido!")
        return
    user = User(user_id=user_id, name=user_text)
    set_user_session(user_id, user.to_dict())
    text_to_send = f"Usuário {user_text} registrado com sucesso!\nAgora você pode adicionar alimentos à sua dieta mandando mensagens de voz, ou texto. ex: '100g banana, 250g maçã'"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)
    return 0

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    user = User.from_dict(get_user_session(user_id))
    
        
# async def inline_caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.inline_query.query
#     if not query:
#         return
#     results = []
#     results.append(
#         InlineQueryResultArticle(
#             id=query.upper(),
#             title='Caps',
#             input_message_content=InputTextMessageContent(query.upper())
#         )
#     )
#     await context.bot.answer_inline_query(update.inline_query.id, results)
    
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
    
    
async def delete_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text_to_send = delete_last_food(user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)

async def get_voice(update: Update, context: CallbackContext):
# get basic info about the voice note file and prepare it for downloading
    user_id = update.message.from_user.id
    new_file = await context.bot.get_file(update.message.voice.file_id)
    file_path = new_file.file_path
    downloaded_file = requests.get(file_path).content
    bio = BytesIO(downloaded_file)
    user_text = transcribe_audio(bio)
    text_to_send = add_food(user_text, user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_send)
    

if __name__ == '__main__':
    import os
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_TOKEN")).build()
    
    add_food_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), register_food)
    help_handler = CommandHandler('help', help)
    delete_food_handler = CommandHandler('deletefood', delete_food)
    start_handler = CommandHandler('start', start)
    get_diet_handler = CommandHandler('today', get_diet)
    # inline_caps_handler = InlineQueryHandler(inline_caps)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    
    # register_handler = ConversationHandler(
    #     entry_points=[CommandHandler("register", register)],
    #     states={
    #         1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
    #     },
    #     fallbacks=[MessageHandler(filters.COMMAND, unknown)]
    # )
    from user_register import make_register
    register_handler = make_register()
    
    application.add_handler(MessageHandler(filters.VOICE, get_voice))
    application.add_handler(help_handler)
    application.add_handler(delete_food_handler)
    application.add_handler(get_diet_handler)
    application.add_handler(register_handler)
    # application.add_handler(inline_caps_handler)
    application.add_handler(start_handler)
    application.add_handler(add_food_handler)
    application.add_handler(unknown_handler)

    
    application.run_polling()
    
    
    
