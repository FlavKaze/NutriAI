from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

from user_structure import calcular_calorias_diarias, calcular_macronutrientes, User
from database import set_user_session, get_user_session, del_user_session


# Definindo os estados da conversa
(NOME, ATUALIZAR, PESO, ALTURA, IDADE, SEXO, NIVEL_ATIVIDADE, OBJETIVO, CALCULAR) = range(9)


def calculate_values(user_id, data):
    calorias_diarias = calcular_calorias_diarias(data['peso'], data['altura'], data['idade'], data['sexo'], data['nivel_atividade'], data['objetivo'])
    carboidratos, proteinas, gorduras, fibras = calcular_macronutrientes(calorias_diarias, data['sexo'])
    user = User(
        user_id=user_id,
        name=data['nome'],
        weight=data['peso'],
        height=data['altura'],
        age=data['idade'],
        gender=data['sexo'],
        activity_level=data['nivel_atividade'],
        objective=data['objetivo'],
        daily_kcal=calorias_diarias,
        daily_carbs=carboidratos,
        daily_protein=proteinas,
        daily_fat=gorduras,
        daily_fiber=fibras
    )
    if get_user_session(user_id):
        old_user = User.from_dict(get_user_session(user_id))
        user.all_diet = old_user.all_diet
        del_user_session(user_id)
        
    set_user_session(user_id, user.to_dict())
    text_to_send = "Recomendações diárias:\n"
    text_to_send += f"Calorias: {calorias_diarias:.2f}\n"
    text_to_send += f"Carboidratos: {carboidratos:.2f}g\n"
    text_to_send += f"Proteínas: {proteinas:.2f}g\n"
    text_to_send += f"Gorduras: {gorduras:.2f}g\n"
    text_to_send += f"Fibras: {fibras}g "
    return text_to_send


# Função para iniciar a conversa
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if get_user_session(user_id):
        await update.message.reply_text("Usuário já cadastrado!")
        reply_keyboard = [['Sim', 'Não']]
        await update.message.reply_text('Deseja atualizar seus dados?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return ATUALIZAR
        
    await update.message.reply_text('Olá! Vamos calcular suas necessidades diárias de calorias e macronutrientes.')
    await update.message.reply_text('Qual é o seu nome?')
    return NOME

async def atualizar(update: Update, context: CallbackContext):
    if update.message.text.lower() == 'sim':
        await update.message.reply_text('Qual é o seu nome?')
        return NOME
    else:
        await update.message.reply_text('Operação cancelada.')
        return ConversationHandler.END

async def nome(update: Update, context: CallbackContext):
    context.user_data['nome'] = update.message.text
    await update.message.reply_text('Olá! Qual é o seu peso em kg?')
    return PESO

# Função para lidar com o peso
async def peso(update: Update, context: CallbackContext):
    user = update.message.from_user
    context.user_data['peso'] = float(update.message.text)
    await update.message.reply_text('Qual é a sua altura em cm?')
    return ALTURA

# Função para lidar com a altura
async def altura(update: Update, context: CallbackContext):
    context.user_data['altura'] = float(update.message.text)
    await update.message.reply_text('Qual é a sua idade?')
    return IDADE

# Função para lidar com a idade
async def idade(update: Update, context: CallbackContext):
    context.user_data['idade'] = int(update.message.text)
    reply_keyboard = [['Masculino', 'Feminino']]
    await update.message.reply_text('Qual é o seu sexo?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return SEXO

# Função para lidar com o sexo
async def sexo(update: Update, context: CallbackContext):
    context.user_data['sexo'] = update.message.text
    reply_keyboard = [['1', '2', '3', '4', '5']]
    await update.message.reply_text('De 1 a 5 qual é seu Nivel de atividade onde 0 é sedentário e 5 é muito ativo?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return NIVEL_ATIVIDADE

# Função para lidar com o nível de atividade
async def nivel_atividade(update: Update, context: CallbackContext):
    context.user_data['nivel_atividade'] = update.message.text
    reply_keyboard = [['Perder peso', 'Manter peso', 'Ganhar peso']]
    await update.message.reply_text('Qual é o seu objetivo com a dieta?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return OBJETIVO

# Função para lidar com o objetivo
async def objetivo(update: Update, context: CallbackContext):
    context.user_data['objetivo'] = update.message.text
    await update.message.reply_text('Vamos calcular suas necessidades diárias de calorias e macronutrientes.', reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(calculate_values(update.message.from_user.id, context.user_data))
    await update.message.reply_text('Agora você pode adicionar alimentos à sua dieta mandando mensagens de voz, ou texto. ex: "100g banana, 250g maçã"')
    return ConversationHandler.END


# Função para cancelar a conversa
async def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Operação cancelada.')
    return ConversationHandler.END

# Configuração do `ConversationHandler`
def make_register():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', start)],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome)],
            ATUALIZAR: [MessageHandler(filters.Regex('^(Sim|Não)$'), atualizar)],
            PESO: [MessageHandler(filters.TEXT & ~filters.COMMAND, peso)],
            ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, altura)],
            IDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, idade)],
            SEXO: [MessageHandler(filters.Regex('^(Masculino|Feminino)$'), sexo)],
            NIVEL_ATIVIDADE: [MessageHandler(filters.Regex('^(1|2|3|4|5)$'), nivel_atividade)],
            OBJETIVO: [MessageHandler(filters.Regex('^(Manter peso|Perder peso|Ganhar peso)$'), objetivo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    return conv_handler
    