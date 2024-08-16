from redis import Redis
try:
    redis_con_bytes = Redis("redis", decode_responses=False)
    redis_con_bytes.time()
except:
    try:
        redis_con_bytes = Redis(decode_responses=False)
        redis_con_bytes.time()
    except:
        redis_con_bytes = None

try:
    redis_con = Redis("redis")
    redis_con.time()
except:
    try:
        redis_con = Redis()
        redis_con.time()
    except:
        redis_con = None
