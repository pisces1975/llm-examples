import requests  
import json  
from utilities.constants import CONST 
import re  
  

def ask_question(question, user_id, limit, mode):  
    url = 'http://localhost:5000/ask'  
    headers = {'Content-Type': 'application/json'}  
    data = {'question': question, 'user_id':user_id, 'limit':limit, 'mode':mode}  

    response = requests.post(url, headers=headers, data=json.dumps(data))  
    if response.status_code == 200:  
        answer = response.json().get('answer')  
        return answer  
    else:  
        error = response.json().get('error')  
        print(f"Error: {error}")  
        return None  


def replace_links(text):  
    pattern = r'<a href="([^"]+)" target="([^"]+)">([^<]+)</a>'  
    return re.sub(pattern, r'[\3](\1)', text) 
# # 示例用法  
# question = "What's the capital of France?"  
# answer = ask_question(question)  
# if answer:  
#     print(f"Answer: {answer}")