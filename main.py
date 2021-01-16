from bert_serving.client import BertClient
import urllib.request
import json
import re
import os
from multiprocessing import Process, Pipe
import numpy as np

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

def fetch_and_find_earliest_use(word):
    return {"word": word, "firstUse": earliest_use(fetch_word(word))}

def fetch_word(word):
    with urllib.request.urlopen(api_path(word, token)) as url:
        resp = url.read().decode()
        data = json.loads(resp)
        return data

## Dictionary can contain multiple entires for a word, find earliest used
def earliest_use(entries):
    # TO-DO: check not obsolete usage
    # TO-DO: follow redirects i.e. follow 'API' to 'application programming interface'
    # DREAM TO-DO: implement analysis to get best usage
    return min([clean_date(entry['date']) for entry in entries if 'date' in entry])

def clean_date(date_string):
    date = int(re.search('[0-9]+', date_string).group())

    # quick and dirty conversion of centuries
    if date < 100:
        date = (date-1) * 100

    return date

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

print(fetch_word('template'))

# with BertClient() as bc:
#     sent_vec = bc.encode([sentence])[0]
#     def_vecs = bc.encode(definitions)
#     scores = np.sum(sent_vec * def_vecs, axis=1) / np.linalg.norm(def_vecs, axis=1)

