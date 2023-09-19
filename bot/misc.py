from telegram.ext import ContextTypes
from smm_api import API
from .db import get_user_db

COMMAND_I = 0

def gci():
    global COMMAND_I

    COMMAND_I += 1
    return COMMAND_I

class STEP:
    class AUTH:
        AUTH = gci()
        HELP = gci()
        LOGGED = gci()
        LOGOUT = gci()
        KEY_GET = gci()

    class MENU:
        ENTRY = gci()
        UNBOUND = gci()
        BALANCE = gci()
        MAKE_ORDER = gci()
        TRACK_ORDERS = gci()
        ADD_ORDER = gci()
        ADD_ORDER_SELECT = gci()
        DELETE_ORDER = gci()
        DELETE_ORDER_SELECT = gci()
        SHOW_ORDER = gci()
        SHOW_ORDER_SUB = gci()
        CHANGE_API = gci()
        CHANGE_API_CANCEL = gci()
        NEXT_PAGE = gci()
        PREV_PAGE = gci()
        NEW_ORDER_SELECT_CATEGORY = gci()
        NEW_ORDER_SELECT_SERVICE = gci()
        NEW_ORDER_EDIT_FIELD = gci()
        SEND_ORDER = gci()
        SEND_ORDER_CONFIRM = gci()
        SUPPORT = gci()

NEW_ORDER_KEYS_DESCRIPTION = {
    'link': ('🔗 Link', 'Link 🔗'),
    'quantity': ('🔢 Quantity', 'Quantity 🔢'),
    'comments': ('💬 Comments', 'Comments (1 per line) 💬'),
    'username': ('👤 Username', 'Username 👤'),
    'new_posts': ('🖼 New Posts', 'New Posts count 🖼'),
    'old_posts': ('🖼 Old Posts', 'Old Posts count 🖼'),
    'delay': ('⏳ Delay', 'Delay in minutes ⏳'),
    'expire': ('📅 Expire', 'Expire date (DD/MM/YYYY) 📅'),
    'usernames': ('👥 Usernames', 'Usernames (one per line) 👥'),
}

ORDER_KEYS_DESCRIPTION = {
    'charge': '💳 Charge',
    'start_count': '🔢 Start Count',
    'status': '🧾 Status',
    'remains': '👥 Remains',
}

ORDER_VALUES_DESCRIPTION = {
    'Completed': 'Completed ✅',
    'Canceled': 'Canceled ❌'
}

def parse_order(d: dict) -> (str, list | None):
    orders = None
    if 'orders' in list(d.keys()):
        orders = d['orders']
        del d['orders']

    text = ''
    for (k, v) in d.items():
        if k == 'currency':
            continue
        
        left = ''
        if k in list(ORDER_KEYS_DESCRIPTION.keys()):
            left = ORDER_KEYS_DESCRIPTION[k]
        else:
            left = '⚙ ' + k.replace('_', ' ').capitalize()

        right = v
        if v in list(ORDER_VALUES_DESCRIPTION.keys()):
            right = ORDER_VALUES_DESCRIPTION[v]
        
        if k == 'charge':
            right = f'${right}'

        text += f'<b>{left}</b>: {right}\n'
    
    return (text, orders)


def get_user_api(context: ContextTypes.DEFAULT_TYPE) -> API:
    if not 'user_api' in list(context.user_data.keys()) or context.user_data['user_api'] == None:
        context.user_data['user_api'] = API(get_user_db(context).get_api_key())
    
    return context.user_data['user_api']

def parse_error(s):
    return f'<b>🚫  An error occured  🚫</b>\n<code>{s}</code>'