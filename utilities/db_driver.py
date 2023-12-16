import mysql.connector
from utilities.logger import LOG
from datetime import datetime, timedelta
from utilities.ConfigReader import Config
import re

# MySQL 数据库连接参数
mysql_db_config = {
    "host": Config.get_config_mysql_host(),
    "user": Config.get_config_mysql_user(),
    "password": Config.get_config_mysql_pwd(),
    "database": Config.get_config_mysql_db()
}

class DBDriver: 
    def __init__(self):
        self.db_connection = mysql.connector.connect(**mysql_db_config)
        self.db_cursor = self.db_connection.cursor()
        if self.db_connection.is_connected():
            LOG.debug("Successfully connect mysql database")
    def __del__(self):    
        # if self.db_cursor:
        self.db_cursor.close()
        self.db_connection.close()
    def execute_query(self, query, params=()):
        self.db_cursor.execute(query, params)
        if query.strip().startswith("SELECT"):
            pass
        else:
            self.db_connection.commit()        

    def get_wiki_id(self, vid) -> str:
        query = '''
            SELECT ID FROM knowledgebase WHERE vector_id = %s AND valid_flag=1
            '''        
        self.execute_query(query, (int(vid),))
        result = self.db_cursor.fetchone()
        if result:
            return result[0]
        else:
            return None       

    def get_text_id(self, vid) -> int:
        query = '''
            SELECT id FROM textpoints_1204 WHERE vector_id = %s AND valid_flag=1
            '''        
        self.execute_query(query, (int(vid),))
        result = self.db_cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

    def create_answer_title(self, answer_list) -> str:        
        sum1 = sum2 = 0        
        for i in answer_list:
            # LOG.debug(type(i))
            if len(i) > 8:
                sum1 += 1
            else:
                sum2 += 1

        return f'找到{len(answer_list)}个答案，包括{sum1}篇参考文章，{sum2}个参考知识点'
        

    def replace_markdown_link_with_html(self, text):
        # 匹配[content](URL)格式的正则表达式模式，用于提取content和URL
        pattern = r'\[(.*?)\]\((https?://\S+?)\)'
        
        # 匹配[content](URL)格式并替换为HTML链接
        def replace_link(match):
            content = match.group(1)
            url = match.group(2)
            if 'pictures' in url:
                content = '（图片）'
            return f'<a href="{url}" target="_blank">{content}</a>'
        
        # 使用re.sub()进行替换
        replaced_text = re.sub(pattern, replace_link, text)
        
        return replaced_text

    def fetch_answer(self, wiki_list) -> list:
        if len(wiki_list) == 0:
            res_list = [{'index':-1, 'content_id':0, 'prefix':'', 'content':"没有找到答案，换个问法吧"}]
        else:
            query1 = '''
                SELECT id, name, description, full_path, URL FROM knowledgebase
                WHERE id=%s
            '''
            query = '''
                SELECT tp.id, tp.content, kb.name, kb.full_path, kb.URL
                FROM textpoints_1204 AS tp
                JOIN knowledgebase AS kb ON tp.wiki_id = kb.ID
                WHERE tp.id = %s
            '''
            # answer = self.create_answer_title(wiki_list)
            res_entity = {'index':0, 'content_id':0, 'prefix': '', 'content':self.create_answer_title(wiki_list)}
            res_list = [res_entity]
            # HREF = '''<a href="{}" target="_blan">{}</a>'''
            for i, item in enumerate(wiki_list):
                summary_flag = False
                if len(item) > 8:
                    self.execute_query(query1, (str(item),))
                    summary_flag = True
                else:
                    self.execute_query(query, (item,))
                    
                row = self.db_cursor.fetchone()

                prefix_str = ''
                if summary_flag:
                    id, name, content, full_path, URL = row
                    prefix_str = '[摘要]'                
                else:
                    id, content, name, full_path, URL = row
                    prefix_str = '[知识点]'
                    # content = self.replace_markdown_link_with_html(content)           

                # href_str = HREF.format(URL, name)
                href_str = URL
                # row_string = f'[{prefix_str}参考#{i+1}][出处：{href_str}]' + content 
                # answer += f"\n{row_string}"
                #res_entity = {'index':i+1, 'content_id':item, 'prefix': f'[{prefix_str}参考#{i+1}][出处：{href_str}]', 'content':content}
                res_entity = {'index':i+1, 'content_id':item, 'prefix': f'（{i+1}）{prefix_str}[[{name}]({URL})]', 'content':content}
                res_list.append(res_entity)

        return res_list