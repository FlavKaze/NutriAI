import json
import redis
import pickle
from typing import Any

def get_redis_connection(db=0, decode_responses=True):
    return redis.Redis(host='localhost', port=6379, decode_responses=decode_responses, db=db)

r = get_redis_connection()

def set_user_session(user_id: int, infos: str):
    return r.set(user_id, json.dumps(infos))
    
def get_user_session(user_id: int):
    return json.loads(r.get(user_id) or '{}')

def del_user_session(user_id: int):
    return r.delete(user_id)

r_foods = get_redis_connection(db=1, decode_responses=False)

def normalize_key(key: str) -> str:
    key = key.replace(' ', '_').lower()
    return key

def set_food_session(food_id: str, foods: Any):
    return r_foods.set(normalize_key(food_id), pickle.dumps(foods))

def get_food_session(food_id: str):
    foods = r_foods.get(normalize_key(food_id))
    if foods:
        return pickle.loads(foods)

def del_food_session(food_id: str):
    return r_foods.delete(normalize_key(food_id))