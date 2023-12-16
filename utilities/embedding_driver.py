from text2vec import SentenceModel
from text2vec import Word2Vec
import time
import faiss
import numpy as np
import json
import mysql.connector
from utilities.ConfigReader import Config
from utilities.logger import LOG
from utilities.string_resource import get_running_state
from utilities.constants import CONST
from utilities.db_driver import DBDriver
import threading
import os
from xinference.client import Client
import sys
import re

fmt = "=========== {:30} ==========="
search_latency_fmt = "search latency = {:.4f}s"

class IndexFile:
    def __init__(self, index_file_name, mode):
        self.index = faiss.read_index(index_file_name)
        self.mode = mode

class embedding_FAISS:
    def __init__(self):        
        if Config.get_config_debug_mode():
            x_addr = "http://10.101.9.50:9998"
        else:
            x_addr = "http://127.0.0.1:9997"
        
        deb_str = f"{get_running_state()} start to connect xinference server at {x_addr}"
        LOG.info(fmt.format(deb_str))
        self.index_text = IndexFile('bge_ms_index_textpoints.faiss',CONST.INDEX_MODE_TEXTPOINT)
        self.index_summary = IndexFile('bge_ms_index_summary.faiss',CONST.INDEX_MODE_WIKI)
        try:
            client = Client(x_addr)            
            model_uid = client.launch_model(model_name="bge-large-zh-v1.5", model_type="embedding")
            self.model = client.get_model(model_uid)
        except Exception as e:
            LOG.error(f"{get_running_state()} Could not connect with xinference server")
            sys.exit(1)

        LOG.info(fmt.format(f"{get_running_state()} Complete connecting xinference server"))
        self.answer_dealer = DBDriver()
    
    def create_embedding_bge(self, sentence):
        result = self.model.create_embedding(sentence)
        embedding = result['data'][0]['embedding']
        # mylogger.debug(f"length of embedding {len(embedding)}, {embedding[:5]}")
        return embedding
    
    def query(self, question, user_id, limit, summary_only_mode):          
        LOG.info(fmt.format(f"{get_running_state()} Start searching based on vector similarity ({user_id}, {limit}, {summary_only_mode}): {question[:20]}"))
        question = [question,""]
        start_time = time.time()
        search_vector = self.create_embedding_bge(question)
        
        if summary_only_mode == CONST.SEARCH_MODE_SUMMARY:
            s_limit = limit
        else:
            s_limit = int(limit/2)+1

        LOG.debug("Start to search summary FAISS db")
        distances_summary, indices_summary = self.index_summary.index.search(np.array([search_vector], dtype=np.float32), s_limit)
        if summary_only_mode == CONST.SEARCH_MODE_MIX:
            LOG.debug("Start to search text FAISS db")
            distances_text, indices_text = self.index_text.index.search(np.array([search_vector], dtype=np.float32), limit)

        end_time = time.time()
        LOG.info(search_latency_fmt.format(end_time - start_time))
        
        wiki_list = []

        for i in range(s_limit):
            index = indices_summary[0][i]
            distance = distances_summary[0][i]
            # content = self.index_summary.mapping.get(str(index), "Unknown Content")                
            content = self.answer_dealer.get_wiki_id(index)
            LOG.info(f"Result {i + 1}> Distance:{distance}, index:{index}, Content:{content}")
            if Config.get_config_threshold() > distance and content: 
                wiki_list.append(content)
        
        if summary_only_mode == CONST.SEARCH_MODE_MIX:
            for i in range(limit):
                index = indices_text[0][i]
                distance = distances_text[0][i]
                #content = self.index_text.mapping.get(str(index), "Unknown Content")    
                content = self.answer_dealer.get_text_id(index)
                LOG.info(f"Result {i + 1}> Distance:{distance}, index:{index}, Content:{content}")
                if Config.get_config_threshold() > distance and content: 
                    wiki_list.append(content)

        result = []
        for i in wiki_list:
            result.append(str(i))

        return result
    
    
    
    

            
