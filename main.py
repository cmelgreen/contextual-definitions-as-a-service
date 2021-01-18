from bert_serving.client import BertClient
import urllib.request
import json
import re
import os
from multiprocessing import Process, Pipe
from merriam_webster_parser import parse_resp
import numpy as np
import time

def lambda_handler(event, context):
    try:
        words = event['multiValueQueryStringParameters']['words']
        first_uses = parallelize(fetch_and_find_earliest_use, words)

        return lambda_response(200, first_uses)

    except Exception as e:
        return lambda_response(400, repr(e))

def lambda_response(code, body):
    return {
        "isBase64Encoded": False,
        "statusCode": code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "multiValueHeaders": {},
        "body": json.dumps(body)
    }

def get_token():
    try:
        return os.environ.get('MERRIAM_WEBSTER_TOKEN')
    except Exception as e:
        return e

api = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={token}'
token = get_token()

def api_path(word, token):
    return api.format(word=word, token=token)


def fetch_word(word):
    with urllib.request.urlopen(api_path(word, token)) as url:
        resp = url.read().decode()
        data = json.loads(resp)
        return data

def parallelize(f, args):
        processes = []
        parent_connections = []

        def parallel_factory(f):
            def parallel_f(conn, arg):
                conn.send(f(arg))
                conn.close()

            return parallel_f

        parallel_f = parallel_factory(f)

        for arg in args:
            parent_conn, child_conn = Pipe()
            parent_connections.append(parent_conn)

            process = Process(target=parallel_f, args=(child_conn, arg))
            processes.append(process)

        for process in processes:
            process.start()

        for process in processes:
            process.join()

        results = []
        for parent_connection in parent_connections:
            results.append(parent_connection.recv())

        return results

def encode_list():
    with BertClient(port=5555, port_out=5556) as bc:
        print(bc.encode(['First do it', 'then do it right', 'then do it better']))



def fetch_and_parse(word):
    return parse_resp(fetch_word(word))

words = ['template', 'balloon', 'overlay', 'boogey']

start = time.time()
words = [fetch_word(word) for word in words]
end = time.time()
print('Raw F: ', end-start)

words = ['template', 'balloon', 'overlay', 'boogey']

start = time.time()
words = parallelize(fetch_word, words)
end = time.time()
print('Fetch: ', end-start)

start = time.time()
words = [parse_resp(word) for word in words]
end = time.time()
print('Parse: ', end-start)

words = ['template', 'balloon', 'overlay', 'boogey']

start = time.time()
words = parallelize(fetch_and_parse, words)
end = time.time()
print('FandP: ', end-start)


# for word in words:
#     for entry in word:
#         print(entry['date'], ": ", entry['def'])

#     print()
