import logging
import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import yaml
from .db import get_user_db
from .misc import STEP, get_user_api, parse_order, parse_error, NEW_ORDER_KEYS_DESCRIPTION, ORDER_KEYS_DESCRIPTION
from smm_api import parse_response, parse_service_list, SERVICE_TYPES_KEYS

MAX_PAGE_SIZE = 8

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    if db.get_api_key() == None:
        return STEP.MENU.UNBOUND
    
    context.user_data['orders_message'] = None
    context.user_data['new_order_message'] = None
    context.user_data['track_orders_page'] = 0
    context.user_data['new_order_category_page'] = 0
    context.user_data['new_order_service_page'] = 0
    context.user_data['services'] = None

    btn_track_order = InlineKeyboardButton('Track Orders 📦', callback_data=STEP.MENU.TRACK_ORDERS)
    btn_new_order = InlineKeyboardButton('Make New Order 📩', callback_data=STEP.MENU.MAKE_ORDER)
    btn_balance = InlineKeyboardButton('Check Balance 💳', callback_data=STEP.MENU.BALANCE)
    btn_support = InlineKeyboardButton('Support 📢', callback_data=STEP.MENU.SUPPORT)
    btn_change_api = InlineKeyboardButton('API key 🔑', callback_data=STEP.MENU.CHANGE_API)
    keyboard = InlineKeyboardMarkup([[btn_track_order], [btn_new_order], [btn_balance], [btn_support, btn_change_api]])

    await context.bot.send_message(chat_id, f'<b>🍃  SMM-HEAVEN BOT  🍃</b>\n', parse_mode=ParseMode.HTML, reply_markup=keyboard)

    return STEP.MENU.ENTRY

async def track_order_next_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['track_orders_page'] += 1

    return await track_order_command(update, context)

async def track_order_prev_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['track_orders_page'] -= 1

    if context.user_data['track_orders_page'] < 0:
        context.user_data['track_orders_page'] = 0

    return await track_order_command(update, context)

async def track_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    orders = db.get_orders()
    btns = []

    pages = (len(orders) - 1) // MAX_PAGE_SIZE + 1
    pages = min(1, pages)
    current_page = context.user_data['track_orders_page']
    page_size = min(len(orders), MAX_PAGE_SIZE)
    if current_page == pages - 1:
        if len(orders) % MAX_PAGE_SIZE != 0:
            page_size = len(orders) % MAX_PAGE_SIZE

    for i in range(page_size):
        btn = InlineKeyboardButton(f'{orders[i+current_page*MAX_PAGE_SIZE]}', callback_data=i+1000+current_page*MAX_PAGE_SIZE)
        btns.append([btn])

    btn_add = InlineKeyboardButton('Add Order ➕', callback_data=STEP.MENU.ADD_ORDER)
    btn_delete = InlineKeyboardButton('Delete Order ➖', callback_data=STEP.MENU.DELETE_ORDER)
    
    pagination = []
    if current_page != 0:
        btn = InlineKeyboardButton('◀ Previous', callback_data=STEP.MENU.PREV_PAGE)
        pagination.append(btn)

    if current_page != pages - 1:
        btn = InlineKeyboardButton('Next ▶', callback_data=STEP.MENU.NEXT_PAGE)
        pagination.append(btn)

    btn_menu = InlineKeyboardButton('Menu 🕹', callback_data=STEP.MENU.ENTRY)
    btns.append([btn_add, btn_delete])
    btns.append(pagination)
    btns.append([btn_menu])

    keyboard = InlineKeyboardMarkup(btns)

    msg: telegram.Message
    if context.user_data['orders_message'] == None:
        msg = await context.bot.send_message(chat_id, f'<b>📦  ORDERS</b>\nHere are your orders. You can add orders manually by order id or track orders made with the Bot.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        msg = context.user_data['orders_message']
        msg = await msg.edit_text(f'<b>📦  ORDERS</b>\nHere are your orders. You can add orders manually by order id or track orders made with the Bot.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    context.user_data['orders_message'] = msg

    return STEP.MENU.TRACK_ORDERS

async def add_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    btn_cancel = InlineKeyboardButton('❌ Cancel', callback_data=STEP.MENU.TRACK_ORDERS)
    keyboard = InlineKeyboardMarkup([[btn_cancel]])

    await context.bot.send_message(chat_id, f'Send Order id 📦', reply_markup=keyboard)
    context.user_data['orders_message'] = None

    return STEP.MENU.ADD_ORDER_SELECT

async def add_order_send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)
    api = get_user_api(context)

    order = update.effective_message.text.strip()
    data = api.order_status(order)
    data = parse_response(data)

    if data[1]:
        msg = parse_error(data[0])
        await context.bot.send_message(chat_id, f'❌ Order {order} coudln\'t be added\n\n{msg}', parse_mode=ParseMode.HTML)
    else:
        order_parsed = parse_order(data[0])
        msg = order_parsed[0]
        
        if order_parsed[1] != None:
            msg += f'<b>📃 Orders:</b> <code>{len(order_parsed[1])}</code>'

        db.add_order(order)
        await context.bot.send_message(chat_id, f'✅ Order <code>{order}</code> succesfully added\n\n{msg}', parse_mode=ParseMode.HTML)

    return await track_order_command(update, context)

async def delete_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_user_db(context)

    orders = db.get_orders()
    btns = []
    current_page = context.user_data['track_orders_page']
    pages = (len(orders) - 1) // MAX_PAGE_SIZE + 1
    pages = min(1, pages)
    page_size = min(len(orders), MAX_PAGE_SIZE)
    if current_page == pages - 1:
        if len(orders) % MAX_PAGE_SIZE != 0:
            page_size = len(orders) % MAX_PAGE_SIZE

    for i in range(page_size):
        btn = InlineKeyboardButton(f'{orders[i+current_page*MAX_PAGE_SIZE]}', callback_data=i+2000+current_page*MAX_PAGE_SIZE)
        btns.append([btn])

    btn_cancel = InlineKeyboardButton('Cancel ❌', callback_data=STEP.MENU.TRACK_ORDERS)
    btns.append([btn_cancel])

    keyboard = InlineKeyboardMarkup(btns)

    msg: Message = context.user_data['orders_message']
    msg = await msg.edit_text('<b>❌ SELECT AN ORDER TO DELETE</b>', reply_markup=keyboard, parse_mode=ParseMode.HTML)

    context.user_data['orders_message'] = msg

    return STEP.MENU.DELETE_ORDER_SELECT

async def delete_order_select_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_user_db(context)
    
    orders = db.get_orders()
    order = update.callback_query.data

    try:
        db.remove_order(orders[int(order) - 2000])
    except BaseException:
        pass

    return await track_order_command(update, context)

async def make_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    api = get_user_api(context)

    services = parse_response(api.service_list())
    btn_menu = InlineKeyboardButton('Menu 🕹', callback_data=STEP.MENU.ENTRY)
    
    if services[1]:
        keyboard = InlineKeyboardMarkup([[btn_menu]])
        await context.bot.send_message(chat_id, f'❌ Couldn\'t load services\n\n{parse_error(services[0])}', reply_markup=keyboard, parse_mode=ParseMode.HTML)

        return STEP.MENU.MAKE_ORDER


    services = parse_service_list(services[0])
    context.user_data['services'] = services
    btns = []
    categories = list(services.keys())

    pages = (len(categories) - 1) // MAX_PAGE_SIZE + 1
    current_page = context.user_data['new_order_category_page']

    btns = []
    page_size = min(len(categories), MAX_PAGE_SIZE)
    if current_page == pages - 1:
        if len(categories) % MAX_PAGE_SIZE != 0:
            page_size = len(categories) % MAX_PAGE_SIZE

    for i in range(page_size):
        btn = InlineKeyboardButton(f'{categories[i+current_page*MAX_PAGE_SIZE]}', callback_data=i+1000+current_page*MAX_PAGE_SIZE)
        btns.append([btn])

    pagination = []
    if current_page != 0:
        btn = InlineKeyboardButton('◀ Previous', callback_data=STEP.MENU.PREV_PAGE)
        pagination.append(btn)

    if current_page != pages - 1:
        btn = InlineKeyboardButton('Next ▶', callback_data=STEP.MENU.NEXT_PAGE)
        pagination.append(btn)


    btns.append(pagination)
    btns.append([btn_menu])

    keyboard = InlineKeyboardMarkup(btns)

    msg: Message
    if context.user_data['new_order_message'] == None:
        msg = await context.bot.send_message(chat_id, f'<b>🧮  SELECT CATEGORY</b>\nYou have to select service category for your new order.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        msg = context.user_data['new_order_message']
        msg = await msg.edit_text(f'<b>🧮  SELECT CATEGORY</b>\nYou have to select service category for your new order.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    context.user_data['new_order_message'] = msg

    context.user_data['category'] = None

    return STEP.MENU.MAKE_ORDER

async def category_select_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    services = context.user_data['services']
    btn_menu = InlineKeyboardButton('Go Back 🔽', callback_data=STEP.MENU.NEW_ORDER_SELECT_CATEGORY)
    
    if context.user_data['category'] == None:
        category_i = int(update.callback_query.data) - 1000
        categories = list(services.keys())
        category = categories[category_i]
        context.user_data['category'] = category

    category = context.user_data['category']

    btns = []
    category_services = services[category]
    context.user_data['category_services'] = category_services
    category_services_names = [c['name'] for c in category_services]

    pages = (len(category_services) - 1) // MAX_PAGE_SIZE + 1
    current_page = context.user_data['new_order_service_page']

    btns = []
    page_size = min(len(category_services), MAX_PAGE_SIZE)
    if current_page == pages - 1:
        if len(category_services) % MAX_PAGE_SIZE != 0:
            page_size = len(category_services) % MAX_PAGE_SIZE

    for i in range(page_size):
        btn = InlineKeyboardButton(f'{category_services_names[i+current_page*MAX_PAGE_SIZE]}', callback_data=i+1000+current_page*MAX_PAGE_SIZE)
        btns.append([btn])

    pagination = []
    if current_page != 0:
        btn = InlineKeyboardButton('◀ Previous', callback_data=STEP.MENU.PREV_PAGE)
        pagination.append(btn)

    if current_page != pages - 1:
        btn = InlineKeyboardButton('Next ▶', callback_data=STEP.MENU.NEXT_PAGE)
        pagination.append(btn)


    btns.append(pagination)
    btns.append([btn_menu])

    keyboard = InlineKeyboardMarkup(btns)

    msg = context.user_data['new_order_message']
    if msg == None:
        msg = await context.bot.send_message(chat_id, f'<b>{category}</b>\n<b>⚙  SELECT SERVICE</b>\nYou have to select service for your new order.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        msg = await msg.edit_text(f'<b>{category}</b>\n<b>⚙  SELECT SERVICE</b>\nYou have to select service for your new order.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    context.user_data['new_order_message'] = msg
    context.user_data['service'] = None
    context.user_data['service_data'] = None

    return STEP.MENU.NEW_ORDER_SELECT_CATEGORY

async def service_select_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    category = context.user_data['category']
    services = context.user_data['services']
    
    if context.user_data['service'] == None:
        service_i = int(update.callback_query.data) - 1000

        service = services[category][service_i]
        context.user_data['service'] = service

    service = context.user_data['service']

    def get_fields_btns(d: dict) -> list:
        btns = []
        items = list(d.items())
        for i in range(len(items)):
            k = items[i][0]
            v = items[i][1]

            if k in list(NEW_ORDER_KEYS_DESCRIPTION.keys()):
                k = NEW_ORDER_KEYS_DESCRIPTION[k][0]
            else:
                k = k.capitalize()

            btn = InlineKeyboardButton(f'{k} - {v}', callback_data=3000+i)
            btns.append([btn])

        return btns

    d = {}
    if context.user_data['service_data'] == None:
        d = SERVICE_TYPES_KEYS[service['type'].lower()]
        d = {k: None for k in d }
    else:
        d = context.user_data['service_data']

    service_descr = ''
    for (k, v) in service.items():
        if (k == 'rate'): v = f'${str(v)} per 1000'

        if k.lower() in ['category', 'type', 'name', 'service', 'dripfeed', 'refill', 'cancel']:
            continue

        service_descr += f'<b>{k.capitalize()}: </b>{v}\n'

    if 'quantity' in list(d.keys()):
        if d['quantity'] != None:
            service_descr += f'<b>{ORDER_KEYS_DESCRIPTION["charge"]}:</b> ${float(service["rate"]) * (int(d["quantity"]) / 1000)}\n'

    if 'min' in list(d.keys()) and 'max' in list(d.keys()):
        if d['min'] != None and d['max'] != None:
            service_descr += f'<b>{ORDER_KEYS_DESCRIPTION["charge"]}:</b> ${float(service["rate"]) * (int(d["min"]) / 1000)} - {float(service["rate"]) * (int(d["max"]) / 1000)}\n'

    msg_text = f'<b>{category}</b>\n<b>{service["name"]}</b>\n{service_descr}\nTo edit your orders\' fields, just tap on them.'

    msg: Message = context.user_data['new_order_message']
    if msg == None:
        btns = get_fields_btns(d)
        btns.append([InlineKeyboardButton('Send Order 📩', callback_data=STEP.MENU.SEND_ORDER_CONFIRM)])
        btns.append([InlineKeyboardButton('Back 🔽', callback_data=STEP.MENU.NEW_ORDER_SELECT_SERVICE)])
        keyboard = InlineKeyboardMarkup(btns)

        msg = await context.bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        btns = get_fields_btns(d)
        btns.append([InlineKeyboardButton('Send Order 📩', callback_data=STEP.MENU.SEND_ORDER_CONFIRM)])
        btns.append([InlineKeyboardButton('Back 🔽', callback_data=STEP.MENU.NEW_ORDER_SELECT_SERVICE)])
        keyboard = InlineKeyboardMarkup(btns)

        msg = await msg.edit_text(msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    context.user_data['service_data'] = d
    context.user_data['new_order_message'] = msg

    return STEP.MENU.NEW_ORDER_SELECT_SERVICE


async def send_order_conf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = context.user_data['category']
    service = context.user_data['service']
    d = context.user_data['service_data']

    service_descr = ''
    for (k, v) in service.items():
        if (k == 'rate'): v = f'${str(v)} per 1000'

        if k.lower() in ['category', 'type', 'name', 'service', 'dripfeed', 'refill', 'cancel']:
            continue

        service_descr += f'<b>{k.capitalize()}: </b>{v}\n'

    service_options = ''
    for (k, v) in d.items():
        if k in list(NEW_ORDER_KEYS_DESCRIPTION.keys()):
            k = NEW_ORDER_KEYS_DESCRIPTION[k][0]
        else:
            k = k.capitalize()

        service_options += f'<b>{k}:</b> {v}\n'

    if 'quantity' in list(d.keys()):
        if d['quantity'] != None:
            service_descr += f'<b>{ORDER_KEYS_DESCRIPTION["charge"]}:</b> ${float(service["rate"]) * (int(d["quantity"]) / 1000)}\n'

    if 'min' in list(d.keys()) and 'max' in list(d.keys()):
        if d['min'] != None and d['max'] != None:
            service_descr += f'<b>{ORDER_KEYS_DESCRIPTION["charge"]}:</b> ${float(service["rate"]) * (int(d["min"]) / 1000)} - {float(service["rate"]) * (int(d["max"]) / 1000)}\n'


    msg_text = f'<b>{category}</b>\n<b>{service["name"]}</b>\n{service_descr}\n{service_options}'

    btn_conf = InlineKeyboardButton('Confirm ✅', callback_data=STEP.MENU.SEND_ORDER)
    btn_cancel = InlineKeyboardButton('Cancel ❌', callback_data=STEP.MENU.NEW_ORDER_SELECT_SERVICE)

    keyboard = InlineKeyboardMarkup([[btn_conf], [btn_cancel]])

    msg = context.user_data['new_order_message']
    msg = await msg.edit_text(msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    context.user_data['new_order_message'] = msg

    return STEP.MENU.SEND_ORDER_CONFIRM

async def send_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)
    service = context.user_data['service']
    api = get_user_api(context)
    d = context.user_data['service_data'].copy()
    d['service'] = service['service']

    res = api.make_order(d)
    res = parse_response(res)

    context.user_data['new_order_message'] = None

    if res[1]:
        await context.bot.send_message(chat_id, f'❌ Couldn\'t make new order\n\n{parse_error(res[0])}', parse_mode=ParseMode.HTML)
        return await service_select_command(update, context)

    menu_button = InlineKeyboardButton('Menu 🕹', callback_data=STEP.MENU.ENTRY)
    keyboard =  InlineKeyboardMarkup([[menu_button]])

    await context.bot.send_message(chat_id, f'✅ Order was sent succesfully. \nYou can check its status in <b>Track Orders</b> menu.', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    order = res[0]
    db.add_order(order['order'])

    return STEP.MENU.ENTRY

async def edit_field_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data['new_order_message'] = None
    field_i = int(update.callback_query.data) - 3000
    d = context.user_data['service_data']
    service = context.user_data['service']

    context.user_data['new_order_message'] = None

    field = list(d.keys())[field_i]
    field_text = ''
    if field in list(NEW_ORDER_KEYS_DESCRIPTION.keys()):
        field_text = NEW_ORDER_KEYS_DESCRIPTION[field][1]
    else:
        field_text = field.capitalize()

    await context.bot.send_message(chat_id, f'Send {field_text}')

    context.user_data['current_field'] = field

    return STEP.MENU.NEW_ORDER_EDIT_FIELD

async def edit_field_select_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    field = context.user_data['current_field']
    d = context.user_data['service_data']
    service = context.user_data['service']
    message = update.effective_message.text.strip()

    if field == 'min':
        try:
            if int(message) < int(service['min']):
                raise BaseException
        except BaseException:
            await context.bot.send_message(chat_id, '🚫 Wrong min value, try again')
            return STEP.MENU.NEW_ORDER_EDIT_FIELD
        
    if field == 'max':
        try:
            if int(message) > int(service['max']):
                raise BaseException
        except BaseException:
            await context.bot.send_message(chat_id, '🚫 Wrong max value, try again')
            return STEP.MENU.NEW_ORDER_EDIT_FIELD
        
    if field == 'quantity':
        try:
            if int(message) > int(service['max']) or int(message) < int(service['min']):
                raise BaseException
        except BaseException:
            await context.bot.send_message(chat_id, '🚫 Wrong quantity value, try again')
            return STEP.MENU.NEW_ORDER_EDIT_FIELD
        
    if field == 'delay': 
        try:
            int(message)
        except BaseException:
            await context.bot.send_message(chat_id, '🚫 Wrong delay value, try again')
            return STEP.MENU.NEW_ORDER_EDIT_FIELD
        
    if field == 'expire': 
        try:
            t = message.split('/')
            if len(t) != 3:
                raise BaseException

        except BaseException:
            await context.bot.send_message(chat_id, '🚫 Wrong expire value, try again')
            return STEP.MENU.NEW_ORDER_EDIT_FIELD
        

    d[field] = message
    context.user_data['service_data'] = d

    return await service_select_command(update, context)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    api = get_user_api(context)

    data = api.get_balance()
    data = parse_response(data)

    if data[1]:
        msg = parse_error(data[0])
        await context.bot.send_message(chat_id, f'❌ Couldn\'t check balance\n\n{msg}', parse_mode=ParseMode.HTML)
    else:
        msg = f'💳 Your balance is <code>${data[0]["balance"]}</code>'
        await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
    
    return STEP.MENU.ENTRY

async def change_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    btn_cancel = InlineKeyboardButton('Cancel ❌', callback_data=STEP.MENU.CHANGE_API_CANCEL)
    keyboard = InlineKeyboardMarkup([[btn_cancel]])

    context.user_data['change_api_message'] = await context.bot.send_message(chat_id, f'Send your new API key 🔑', reply_markup=keyboard)

    return STEP.MENU.CHANGE_API

async def cancel_change_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg: Message = context.user_data['change_api_message']
    await msg.delete()

    return STEP.MENU.ENTRY

async def change_api_select_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db = get_user_db(context)

    msg = update.effective_message.text
    key = msg.strip()

    if len(key) != 32:
        btn_cancel = InlineKeyboardButton('Cancel ❌', callback_data=STEP.MENU.ENTRY)
        keyboard = InlineKeyboardMarkup([[btn_cancel]])

        await context.bot.send_message(chat_id, f'Invalid API key, try again 🚫', reply_markup=keyboard)

        return STEP.MENU.CHANGE_API
    else:
        await context.bot.send_message(chat_id, f'API key changed ✨')
        db.set_api_key(key)
        context.user_data['user_api'] = None

        return await menu_command(update, context)
    
async def show_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api = get_user_api(context)
    db = get_user_db(context)    

    orders = db.get_orders()
    order_i = int(update.callback_query.data) - 1000
    order = orders[order_i]
    context.user_data['order'] = None

    btns = []

    msg_text = None
    order_data = parse_response(api.order_status(order))
    if order_data[1]:
        msg_text = parse_error(order_data[0])
    else:
        order_data = parse_order(order_data[0])
        orders_sub = order_data[1]
        msg_text = order_data[0]
        if orders_sub != None:
            context.user_data['order'] = (order, order_i, orders_sub)

            for i in range(len(orders_sub)):
                btn = InlineKeyboardButton(orders_sub[i], callback_data=1000+i)
                btns.append([btn])

    btn_track_orders = InlineKeyboardButton('Back to orders 📦', callback_data=STEP.MENU.TRACK_ORDERS)
    btns.append([btn_track_orders])
    
    keyboard = InlineKeyboardMarkup(btns)
    msg: Message = context.user_data['orders_message']
    msg = await msg.edit_text(f'<b>📦  ORDER</b> <code>{order}</code>\n\n{msg_text}', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    context.user_data['orders_message'] = msg

    return STEP.MENU.SHOW_ORDER
    
async def show_sub_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api = get_user_api(context)

    order = context.user_data['order']
    sub_order_i = int(update.callback_query.data) - 1000
    sub_order = order[2][sub_order_i]

    msg_text = None
    order_data = parse_response(api.order_status(sub_order))
    if order_data[1]:
        msg_text = parse_error(order_data[0])
    else:
        order_data = parse_order(order_data[0])
        msg_text = order_data[0]

    btn_show_order = InlineKeyboardButton(f'Back to order {order[0]} 📦', callback_data=1000 + order[1])
    keyboard = InlineKeyboardMarkup([[btn_show_order]])
    msg: Message = context.user_data['orders_message']
    msg = await msg.edit_text(f'<b>📦  SUB ORDER</b> <code>{sub_order}</code>\n\n{msg_text}', reply_markup=keyboard, parse_mode=ParseMode.HTML)
    context.user_data['orders_message'] = msg

    return STEP.MENU.SHOW_ORDER_SUB

async def category_next_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_order_category_page'] += 1

    return await make_order_command(update, context)

async def category_prev_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_order_category_page'] -= 1

    if context.user_data['new_order_category_page'] < 0:
        context.user_data['new_order_category_page'] = 0

    return await make_order_command(update, context)

async def service_next_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_order_service_page'] += 1

    return await category_select_command(update, context)

async def service_prev_page_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_order_service_page'] -= 1

    if context.user_data['new_order_service_page'] < 0:
        context.user_data['new_order_service_page'] = 0

    return await category_select_command(update, context)