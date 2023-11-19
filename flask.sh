#!/bin/bash

flask db init
flask db migrate -m "initial migration"
flask db upgrade
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application
python -c 'redis_client = redis.StrictRedis(host='redis',port=6379,decode_responses=True) ;redis_client.get()'
