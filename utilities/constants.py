from utilities.logger import LOG 
import os
import threading
from xinference.client import Client

class constants:
    def __init__(self):
        self.CHAT_LEVEL_E4 = 2
        self.CHAT_LEVEL_E3 = 1
        self.CHAT_LEVEL_NONE = 0
        # self.NO_FINDING = '没有找到答案, 换个问法试试？'
        self.INDEX_MODE_TEXTPOINT = 0
        self.INDEX_MODE_WIKI = 1
        self.CHAT_MODE_EMBEDDING = 0
        self.CHAT_MODE_QUESTION = 1
        self.CHAT_MODE_SUMMARY = 2
        self.SEARCH_MODE_SUMMARY = 0
        self.SEARCH_MODE_MIX = 1
        self.SEARCH_MODE_STR_ON = "打开"
        self.SEARCH_MODE_STR_OFF = "关闭"
        with open('keywords.csv', 'r', encoding='utf-8') as file:
            line = file.readline().strip()
        self.keywords = line.split(',')
        pid = os.getpid()
        tid = threading.get_ident()
        LOG.debug(f"{pid} Succesfully load {len(self.keywords)} keywords")
        # x_addr = 'http://127.0.0.1:9997'
        # client = Client(x_addr)            
        # model_uid = client.launch_model(model_name="bge-large-zh-v1.5", model_type="embedding")
        # self.model = client.get_model(model_uid)
        # LOG.debug(f"{pid} Succesfully connect load xinference server")

    
    def validate(self, content) -> bool:
        contains_keyword = any(keyword in content for keyword in self.keywords)
        
        if contains_keyword:
            LOG.debug(f"命中关键词，不通过")
            return False # 命中关键词，不通过
        else:
            LOG.debug(f"没有命中关键词，通过")
            return True # 没有命中关键词，通过

CONST = constants()