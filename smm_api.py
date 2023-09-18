import json
import requests
from urllib.parse import urlencode

URL = ''

SERVICE_TYPES_KEYS = {
    'default': ['link', 'quantity'],
    'custom comments': ['link', 'comments'],
    'subscriptions': ['username', 'new_posts', 'old_posts', 'min', 'max', 'delay', 'expire'],
    'mentions custom list': ['link', 'usernames'],
    'package': ['link'],
    'mentions user followers': ['link', 'quantity', 'username'],
    'custom comments package': ['link', 'comments'],
}

class API:
    def __init__(self, key) -> None:
        self.key = key

    def service_list(self) -> list:
        res = requests.post(URL, params=f'key={self.key}&action=services')
        o = json.loads(res.text)
        return o
    
    def make_order(self, params: dict) -> int:
        params['key'] = self.key
        params['action'] = 'add'

        res = requests.post(URL, params=urlencode(params))
        o = json.loads(res.text)
        return o
    
    def order_status(self, order_id: int) -> dict:
        params = {
            'key': self.key,
            'action': 'status',
            'order': order_id
        }

        res = requests.post(URL, params=urlencode(params))
        o = json.loads(res.text)
        return o
    
    def refill_status(self, refill_id: int) -> str | dict:
        params = {
            'key': self.key,
            'action': 'refill_status',
            'refill': refill_id
        }

        res = requests.post(URL, params=urlencode(params))
        o = json.loads(res.text)
        return o
    
    def create_refill(self, order_id: int) -> dict:
        params = {
            'key': self.key,
            'action': 'refill',
            'order': order_id
        }

        res = requests.post(URL, params=urlencode(params))
        o = json.loads(res.text)
        return o
    
    def get_balance(self) -> dict:
        params = {
            'key': self.key,
            'action': 'balance',
        }

        res = requests.post(URL, params=urlencode(params))
        o = json.loads(res.text)
        return o
    
def parse_response(r: dict | str) -> (str, bool):
    if type(r) != dict:
        return (r, False)

    keys = list(r.keys())
    if 'error' in keys:
        return (r['error'], True)
    
    return (r, False)

def parse_service_list(l: list) -> dict:
    d = {}
    categories = set()
    
    for v in l:
        categories.add(v['category'])
    
    categories = list(categories)
    t = list(filter(lambda x: not x.startswith('🌏'),  categories))
    categories = list(filter(lambda x: x.startswith('🌏'),  categories))

    categories = t + categories

    for c in categories:
        d[c] = []

    for v in l:
        v['name'] = f'({v["service"]}) {v["name"]}'
        d[v['category']].append(v)
    
    return d