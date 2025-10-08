import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

data_str = r.get('commande:cmd1')
data_json = json.loads(data_str)
print(json.dumps(data_json, indent=4, ensure_ascii=False))