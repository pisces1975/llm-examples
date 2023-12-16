from flask import Flask, request, jsonify  
from utilities.logger import LOG
from utilities.string_resource import get_running_state
from utilities.ConfigReader import ConfigReader
from utilities.db_driver import DBDriver
from utilities.embedding_driver import embedding_FAISS

app = Flask(__name__)  

db_driver = DBDriver()
emb_driver = embedding_FAISS()

@app.route('/ping', methods=['GET'])
def ping():
    return f'{get_running_state()} pong'

@app.route('/ask', methods=['POST'])  
def ask_question():  
    content_type = request.headers.get('Content-Type')  
    if content_type == 'application/json':  
        question = request.get_json().get('question')  
        user_id = request.get_json().get('user_id')
        limit = int(request.get_json().get('limit'))
        mode = int(request.get_json().get('mode'))
        if question:  
            # 在这里编写处理问题的逻辑代码  
            wiki_list = emb_driver.query(question, user_id, limit, mode)
            answer = db_driver.fetch_answer(wiki_list)
            response = {'answer': answer}  
            return jsonify(response)  
        else:  
            error = {'error': 'Missing question in the request.'}  
            return jsonify(error), 400  
    else:  
        error = {'error': 'Invalid request content type.'}  
        return jsonify(error), 415  

  
if __name__ == '__main__':  
    app.run(host='0.0.0.0', port=5000, debug=True)