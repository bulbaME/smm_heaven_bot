from telegram.ext import ContextTypes
from pymongo import MongoClient
import yaml

CONNECT = yaml.safe_load(open('credentials.yaml'))['mongodb']['connect']
DB = MongoClient(CONNECT).get_database('smm-heaven-bot')

class UserDB:
    def __init__(self, id: int):
        self.id = id
        if DB.users.find_one(filter={'id': id}) == None:
            DB.users.insert_one({
                'id': id,
                'api_key': None,
                'orders': [],
                'support': 0
            })

    def get_api_key(self):
        u = DB.users.find_one(filter={'id': self.id})
        return u['api_key']
    
    def set_api_key(self, key: str | None):
        DB.users.update_one({'id': self.id}, {'$set': {'api_key': key}})

    def add_order(self, order_id):
        DB.users.update_one({'id': self.id}, {'$addToSet': {'orders': order_id}})

    def remove_order(self, order_id):
        DB.users.update_one({'id': self.id}, {'$pull': {'orders': order_id}})

    def get_orders(self):
        u = DB.users.find_one({'id': self.id})
        orders = u['orders']
        orders.reverse()

        return orders
    
    def dec_support_appeal(self):
        DB.users.update_one({'id': self.id}, {'$inc': {'support': -1}})

    def dec_support_appeal_by_id(id: int):
        DB.users.update_one({'id': id}, {'$inc': {'support': -1}})

    def get_support_appeal(self):
        u = DB.users.find_one(filter={'id': self.id})
        return u['support']
    
    def get_support_appeal_by_id(id: int):
        u = DB.users.find_one(filter={'id': id})
        return u['support']
    
    def inc_support_appeal(self):
        DB.users.update_one({'id': self.id}, {'$inc': {'support': 1}})
    
def get_user_db(context: ContextTypes.DEFAULT_TYPE) -> UserDB:
    if not 'user_db' in list(context.user_data.keys()):
        context.user_data['user_db'] = UserDB(context._user_id)
    
    return context.user_data['user_db']
