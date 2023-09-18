import logging
import telegram
from telegram import Update, MenuButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode
import yaml
from .db import get_user_db
from .misc import STEP
from . import menu

TOKEN = yaml.safe_load(open('credentials.yaml'))['tg']['token']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    if db.get_api_key() == None:
        
        btn_tutorial = InlineKeyboardButton('❓ Where do I find my API key ❓', callback_data=STEP.AUTH.HELP)
        btn_api = InlineKeyboardButton('Paste API key 🔑', callback_data=STEP.AUTH.KEY_GET)
        keyboard = InlineKeyboardMarkup([[btn_tutorial], [btn_api]])

        await context.bot.send_message(chat_id, f'<b>🍃  SMM-HEAVEN BOT  🍃</b>\nWelcome, to continue I need your account API key', parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
        return STEP.AUTH.AUTH
    else:
        btn_logout = InlineKeyboardButton('Logout 🚫', callback_data=STEP.AUTH.LOGOUT)
        keyboard = InlineKeyboardMarkup([[btn_logout]])

        await context.bot.send_message(chat_id, f'You are already logged in trough you API key ✨', reply_markup=keyboard)

        return STEP.AUTH.LOGGED

async def send_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, f'Send Your API key 🔑')

    return STEP.AUTH.KEY_GET

async def get_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    msg = update.effective_message.text
    key = msg.strip()

    if len(key) != 32:
        await context.bot.send_message(chat_id, f'Invalid API key, try again 🚫')

        return STEP.AUTH.KEY_GET
    else:
        await context.bot.send_message(chat_id, f'Logged in through API key ✨')
        db.set_api_key(key)

        commands = [
            BotCommand('menu', 'Menu 🍃'),
            BotCommand('logout', 'Logout 🚫'),
        ]
        await context.bot.set_my_commands(commands, scope=telegram.BotCommandScopeChat(chat_id))
        await context.bot.set_chat_menu_button(chat_id, MenuButton(MenuButton.COMMANDS))

        return STEP.AUTH.LOGGED


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    db.set_api_key(None)

    await context.bot.delete_my_commands(scope=telegram.BotCommandScopeChat(chat_id))
    await context.bot.set_chat_menu_button(chat_id, MenuButton(MenuButton.DEFAULT))

    btn = KeyboardButton('/start')
    keyboard = ReplyKeyboardMarkup([[btn]], one_time_keyboard=True, resize_keyboard=True)
    context.user_data['user_api'] = None

    await context.bot.send_message(chat_id, f'Logged out succesfully 🚫', reply_markup=keyboard)

    return STEP.AUTH.LOGOUT

async def suggest_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, 'Try /start')

    return STEP.AUTH.LOGOUT

async def tutorial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    btn = InlineKeyboardButton('Paste API key 🔑', callback_data=STEP.AUTH.KEY_GET)
    keyboard = InlineKeyboardMarkup([[btn]])
    await context.bot.send_photo(chat_id, open('api_key_tutorial.jpg', 'rb'), reply_markup=keyboard)

    return STEP.AUTH.AUTH

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start_command)
    logout_handler = CommandHandler('logout', logout_command)
    menu_handler = CommandHandler('menu', menu.menu_command)

    auth_conversation = ConversationHandler(
        [start_handler],
        {
            STEP.AUTH.AUTH: [
                CallbackQueryHandler(tutorial_command, pattern=f'^{STEP.AUTH.HELP}$'),
                CallbackQueryHandler(send_key_command, pattern=f'^{STEP.AUTH.KEY_GET}$')
            ],
            STEP.AUTH.KEY_GET: [
                start_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_key_command)
            ],
            STEP.AUTH.LOGGED: [
                start_handler,
                logout_handler,
                CallbackQueryHandler(logout_command, pattern=f'^{STEP.AUTH.LOGOUT}$'),
            ],
            STEP.AUTH.LOGOUT: [
                start_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, suggest_start_command)
            ]
        },
        []
    )

    menu_conversation = ConversationHandler(
        [menu_handler],
        {
            STEP.MENU.ENTRY: [
                CallbackQueryHandler(menu.track_order_command, pattern=f'^{STEP.MENU.TRACK_ORDERS}$'),
                CallbackQueryHandler(menu.make_order_command, pattern=f'^{STEP.MENU.MAKE_ORDER}$'),
                CallbackQueryHandler(menu.balance_command, pattern=f'^{STEP.MENU.BALANCE}$'),
                CallbackQueryHandler(menu.change_api_command, pattern=f'^{STEP.MENU.CHANGE_API}$'),
                CallbackQueryHandler(menu.menu_command, pattern=f'^{STEP.MENU.ENTRY}$'),
            ],
            STEP.MENU.CHANGE_API: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu.change_api_select_command),
                CallbackQueryHandler(menu.cancel_change_api_command, pattern=f'^{STEP.MENU.CHANGE_API_CANCEL}$'),
                CallbackQueryHandler(menu.menu_command, pattern=f'^{STEP.MENU.ENTRY}$'),
            ],
            STEP.MENU.TRACK_ORDERS: [
                CallbackQueryHandler(menu.show_order_command, pattern=f'^(?:100[0-9]|10[1-9][0-9]|1[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.add_order_command, pattern=f'^{STEP.MENU.ADD_ORDER}$'),
                CallbackQueryHandler(menu.delete_order_command, pattern=f'^{STEP.MENU.DELETE_ORDER}$'),
                CallbackQueryHandler(menu.track_order_next_page_command, pattern=f'^{STEP.MENU.NEXT_PAGE}$'),
                CallbackQueryHandler(menu.track_order_prev_page_command, pattern=f'^{STEP.MENU.PREV_PAGE}$'),
                CallbackQueryHandler(menu.menu_command, pattern=f'^{STEP.MENU.ENTRY}$'),
            ],
            STEP.MENU.ADD_ORDER_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu.add_order_send_command),
                CallbackQueryHandler(menu.track_order_command, pattern=f'^{STEP.MENU.TRACK_ORDERS}$'),
            ],
            STEP.MENU.DELETE_ORDER_SELECT: [
                CallbackQueryHandler(menu.delete_order_select_command, pattern=f'^(?:200[0-9]|20[1-9][0-9]|2[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.track_order_command, pattern=f'^{STEP.MENU.TRACK_ORDERS}$'),
            ],
            STEP.MENU.SHOW_ORDER: [
                CallbackQueryHandler(menu.show_sub_order_command, pattern=f'^(?:100[0-9]|10[1-9][0-9]|1[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.track_order_command, pattern=f'^{STEP.MENU.TRACK_ORDERS}$'),
            ],
            STEP.MENU.SHOW_ORDER_SUB: [
                CallbackQueryHandler(menu.show_order_command, pattern=f'^(?:100[0-9]|10[1-9][0-9]|1[1-4][0-9]{{2}})$'),
            ],
            STEP.MENU.MAKE_ORDER: [
                CallbackQueryHandler(menu.category_select_command, pattern=f'^(?:100[0-9]|10[1-9][0-9]|1[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.category_next_page_command, pattern=f'^{STEP.MENU.NEXT_PAGE}$'),
                CallbackQueryHandler(menu.category_prev_page_command, pattern=f'^{STEP.MENU.PREV_PAGE}$'),
                CallbackQueryHandler(menu.menu_command, pattern=f'^{STEP.MENU.ENTRY}$'),
            ],
            STEP.MENU.NEW_ORDER_SELECT_CATEGORY: [
                CallbackQueryHandler(menu.service_select_command, pattern=f'^(?:100[0-9]|10[1-9][0-9]|1[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.make_order_command, pattern=f'^{STEP.MENU.NEW_ORDER_SELECT_CATEGORY}$'),
                CallbackQueryHandler(menu.service_next_page_command, pattern=f'^{STEP.MENU.NEXT_PAGE}$'),
                CallbackQueryHandler(menu.service_prev_page_command, pattern=f'^{STEP.MENU.PREV_PAGE}$'),
            ],
            STEP.MENU.NEW_ORDER_SELECT_SERVICE: [
                CallbackQueryHandler(menu.edit_field_command, pattern=f'^(?:300[0-9]|30[1-9][0-9]|3[1-4][0-9]{{2}})$'),
                CallbackQueryHandler(menu.category_select_command, pattern=f'^{STEP.MENU.NEW_ORDER_SELECT_SERVICE}$'),
                CallbackQueryHandler(menu.send_order_conf_command, pattern=f'^{STEP.MENU.SEND_ORDER_CONFIRM}$'),
            ],
            STEP.MENU.SEND_ORDER_CONFIRM: [
                CallbackQueryHandler(menu.send_order_command, pattern=f'^{STEP.MENU.SEND_ORDER}$'),
                CallbackQueryHandler(menu.service_select_command, pattern=f'^{STEP.MENU.NEW_ORDER_SELECT_SERVICE}$'),
            ],
            STEP.MENU.NEW_ORDER_EDIT_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu.edit_field_select_command)
            ],
            STEP.MENU.UNBOUND: [menu_handler]
        },
        [],
        allow_reentry=True
    )

    application.add_handlers([auth_conversation, menu_conversation, logout_handler])

    application.run_polling()