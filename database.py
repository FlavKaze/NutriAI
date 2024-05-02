import json
import redis

def get_redis_connection(db=0):
    return redis.Redis(host='localhost', port=6379, decode_responses=True, db=db)

r = get_redis_connection()

def set_user_session(user_id: int, infos: str):
    return r.set(user_id, json.dumps(infos))
    
def get_user_session(user_id: int):
    return json.loads(r.get(user_id) or '{}')

def del_user_session(user_id: int):
    return r.delete(user_id)
