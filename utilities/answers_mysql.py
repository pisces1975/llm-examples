import mysql.connector
from utilities.logger import LOG
from datetime import datetime, timedelta
from utilities.ConfigReader import Config
from utilities.sha_tools import generate_sha_digest
from utilities.constants import CONST
import re

# MySQL 数据库连接参数
mysql_db_config = {
    "host": Config.get_config_mysql_host(),
    "user": Config.get_config_mysql_user(),
    "password": Config.get_config_mysql_pwd(),
    "database": Config.get_config_mysql_db()
}

# workspace_id = '36446663'
class AnswersMySQL:
    def __init__(self, userid):          
        self.user_id = userid                
        self.length_limit = Config.get_config_length()
        self.db_connection = mysql.connector.connect(**mysql_db_config)
        self.db_cursor = self.db_connection.cursor()
        if self.db_connection.is_connected():
            LOG.debug("Successfully connect mysql database")
            flag = self.insert_user()
            if flag:
                # default user will use 文心一言 3.0
                self.update_user_chat_permission(CONST.CHAT_LEVEL_E3) 
                self.update_token(30000)
                self.update_user_optflg(1)
        
        # self.db_cursor = None

        # try:
        #     self.db_connection = mysql.connector.connect(**mysql_db_config)
        #     self.db_cursor = self.db_connection.cursor()
        #     if self.db_connection.is_connected():
        #         LOG.debug("Successfully connect mysql database")
        #         self.insert_user()
        #     else:
        #         self.db_connection = None
        #         self.db_cursor = None
        #         LOG.error("Could not connect mysql database, try later")
        # except Exception as e:
        #     self.db_connection = None
        #     self.db_cursor = None
        #     LOG.error("Could not connect mysql database, try later")
    
    def __del__(self):    
        # if self.db_cursor:
        self.db_cursor.close()
        self.db_connection.close()
    
    
        
    def execute_query(self, query, params=()):
        # if self.db_cursor == None:
        #     self.db_connection = mysql.connector.connect(**mysql_db_config)
        #     self.db_cursor = self.db_connection.cursor()
        #     if self.db_connection.is_connected():
        #         LOG.debug("Successfully connect mysql database")
        #         self.insert_user()
        #     else:
        #         self.db_connection = None
        #         self.db_cursor = None
        #         LOG.error("Could not connect mysql database, try later")
        #         raise Exception("Could not connect mysql DB")
        
        # self.db_cursor.fetchall() 
        # LOG.debug(f"start execute SQL: [{query}]")
        self.db_cursor.execute(query, params)
        if query.strip().startswith("SELECT"):
            pass
        else:
            self.db_connection.commit()    

    # # 检查用户是否存在
    # def check_user_exists(self):
    #     query = '''
    #         SELECT COUNT(*) FROM users 
    #         WHERE user_id = %s    
    #         '''
    #     self.execute_query(query, (self.user_id,))
    #     user_count = self.db_cursor.fetchone()[0]
    #     return user_count > 0

    # # 插入用户信息
    # def insert_user_inner(self):    
    #     query = '''
    #         INSERT INTO users (user_id, recent_question_id, last_answer_id, max_answer_count)
    #         VALUES (%s, NULL, 0, 5)
    #     '''
    #     self.execute_query(query, (self.user_id,))        
    #     LOG.info(f"User {self.user_id} inserted successfully.")

    def insert_user(self) -> bool:
        # if not self.check_user_exists():    
        #     self.insert_user_inner()
        query = '''
            INSERT IGNORE INTO users (user_id, recent_question_id, last_answer_id, max_answer_count)
            VALUES (%s, NULL, 0, 5)
        '''
        self.execute_query(query, (self.user_id,))        
        if self.db_cursor.rowcount > 0:
            LOG.debug(f"Created user {self.user_id}")
            return True
        else:
            LOG.debug(f"User {self.user_id} already exists")   
            return False

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
        
    def get_maintenance_mode(self) -> bool:
        query = '''
            SELECT maintenanceflag FROM users WHERE user_id=%s
            '''
        self.execute_query(query, (self.user_id,))
        result = self.db_cursor.fetchone()[0]
        if result==0:
            return False
        else:
            return True
    
    def insert_chat_question(self, question) -> int:
        insert_query = '''
            INSERT INTO chat_history (USER_ID, question, time, answer, num_token, answer_flag)
            VALUES (%s, %s, CURRENT_TIMESTAMP, NULL, 0, 0);
        '''
        self.execute_query(insert_query, (self.user_id, question))
        
        select_query = 'SELECT LAST_INSERT_ID();'
        self.execute_query(select_query)
        inserted_id = self.db_cursor.fetchone()[0]

        LOG.debug(f"Inserted ({question[:40]}) with ID: {inserted_id}")
        return inserted_id
    
    def insert_chat_answer(self, question_id, answer, token):
        update_query = '''
            UPDATE chat_history
            SET answer = %s, num_token = %s, answer_flag = 0
            WHERE id = %s;
        '''
        self.execute_query(update_query, (answer, token, question_id))
        self.reduce_token(token)
    
    def get_chat_answer(self):
        query = '''
            SELECT id, question, answer, num_token
            FROM chat_history
            WHERE USER_ID = %s
            ORDER BY time DESC
            LIMIT 1;
            '''
        self.execute_query(query, (self.user_id,))
        result = self.db_cursor.fetchone()

        if result:
            id, question, answer, token = result
            if answer:
                LOG.debug(f"【Q{id}】【Answer】{answer[:120]}")
                result_str = answer
            else:
                LOG.debug(f"【Q{id}】your answer is on the way")
                result_str = f'这个问题 ({id})({question[0:80]}) 的答案文心一言还没有返回，请耐心等待一下'                
        else:
            LOG.error("No record found for the given user_id.")
            result_str = f'在历史记录中没有发现这个问题'
            token = 0
        
        return result_str, token

    def get_last_question_id(self, question_content):
        # return None
        current_time = datetime.now()
        twenty_minutes_ago = current_time - timedelta(minutes=Config.get_config_timespan())
        
        query = """
            SELECT question_id
            FROM questions
            WHERE user_id = %s AND question_content = %s AND question_time >= %s 
            ORDER BY question_time DESC
            LIMIT 1
        """
        self.execute_query(query, (self.user_id, question_content, twenty_minutes_ago))
        result = self.db_cursor.fetchone()
        
        if result:
            return result[0]
        else:
            return None
        
    # 更新用户表中的最近问题ID
    def update_user_recent_question_id(self, question_id):
        query = '''
            UPDATE users
            SET recent_question_id = %s, last_answer_id = %s
            WHERE user_id = %s
            '''
        self.execute_query(query, (question_id, 0, self.user_id,))

    def update_user_optflg(self, flag):
        query = '''
            UPDATE users
            SET optflg = %s WHERE user_id = %s
            '''
        self.execute_query(query, (flag, self.user_id,))
        LOG.info(f"Set optimization flag of {self.user_id} to {flag}")
    
    def get_user_optflg(self):
        query = '''
            SELECT optflg FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        flag = self.db_cursor.fetchone()[0]
        if flag == 0:
            return False
        else:
            return True

    def update_user_summary_flag(self, flag):
        query = '''
            UPDATE users
            SET summaryflag = %s WHERE user_id = %s
            '''
        self.execute_query(query, (flag, self.user_id,))
        LOG.info(f"Set summary mode flag of {self.user_id} to {flag}")
    
    def get_user_summary_flag(self):
        query = '''
            SELECT summaryflag FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        flag = self.db_cursor.fetchone()[0]
        if flag == 0:
            return False
        else:
            return True
    
    def get_user_chat_flag(self):
        query = '''
            SELECT chat_flag FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        flag = self.db_cursor.fetchone()[0]
        if flag == 0:
            return False
        else:
            return True
        
    def get_recent_chat_history(self, number) -> list:    
        query = """
            SELECT question, answer
            FROM chat_history
            WHERE USER_ID = %s
            ORDER BY time DESC
            LIMIT %s
            """
    
        self.execute_query(query, (self.user_id, int(number)))
        results = self.db_cursor.fetchall()

        messages = []
        for item in results:
            if item[1]:
                if len(item[1])>0:
                    message_user = {'role':'user', 'content':item[0]}
                    message_assit = {'role':'assistant', 'content':item[1]}
                    messages.append(message_user)
                    messages.append(message_assit)   

        return messages

    
    def update_user_chat_flag(self, flag):
        query = '''
            UPDATE users
            SET chat_flag = %s WHERE user_id = %s
            '''
        self.execute_query(query, (flag, self.user_id,))
        LOG.info(f"Set chat mode flag of {self.user_id} to {flag}")

    def update_user_chat_permission(self, flag):
        query = '''
            UPDATE users
            SET chat_permission = %s WHERE user_id = %s
            '''
        self.execute_query(query, (flag, self.user_id,))
        LOG.info(f"Set chat permission of {self.user_id} to {flag}")
    
    def get_user_chat_permission(self):
        query = '''
            SELECT chat_permission FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        flag = self.db_cursor.fetchone()[0]
        return flag
        
    
    def get_user_number_token(self) ->int:
        query = '''
            SELECT token FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        return int(self.db_cursor.fetchone()[0])
    
    def reduce_token(self, number):
        update_query = "UPDATE users SET token = token - %s WHERE user_id = %s"
        self.execute_query(update_query, (number, self.user_id))
        return

    def update_token(self, number):
        update_query = "UPDATE users SET token = %s WHERE user_id = %s"
        self.execute_query(update_query, (number, self.user_id))
        return
    
    # def update_token(self, number):
    #     update_query = "UPDATE users SET token = %s WHERE user_id = %s"
    #     self.execute_query(update_query, (number, self.user_id))
    #     return
    
    def update_user_mobile_flag(self, flag):
        query = '''
            UPDATE users
            SET mobileflag = %s WHERE user_id = %s
            '''
        self.execute_query(query, (flag, self.user_id,))
        LOG.info(f"Set mobile mode flag of {self.user_id} to {flag}")
    
    def get_user_mobile_flag(self):
        query = '''
            SELECT mobileflag FROM users WHERE user_id =%s
            '''
        self.execute_query(query, (self.user_id,))

        flag = self.db_cursor.fetchone()[0]
        if flag == 0:
            return False
        else:
            return True    

    def get_limit(self):
        query = '''
            SELECT max_answer_count FROM users WHERE user_id = %s
        '''
        self.db_cursor.execute(query, (self.user_id,))
        return self.db_cursor.fetchone()[0]
    
    def add_question_answers(self, question_content, answer_list, llm_answer):           
        question_time = datetime.now()
        if len(answer_list) > 0:
            answer_sequence = ','.join(map(str, answer_list))
        else:
            answer_sequence = '     '        
        
        query = '''
            INSERT INTO questions (question_content, user_id, question_time, answer_sequence_list, llm_answer)
            VALUES (%s, %s, %s, %s, %s)
        '''
        self.execute_query(query, (question_content, self.user_id, question_time, answer_sequence, llm_answer,))
        # inserted_id = self.db_cursor.lastrowid
        # self.update_user_recent_question_id(inserted_id)
        self.update_user_recent_question_id(self.db_cursor.lastrowid)

        LOG.info(f"Question {self.db_cursor.lastrowid} and {len(answer_list)} answers inserted successfully, LLM answer {len(llm_answer)}.")
        if  len(answer_list) == 0:
            return False
        else:
            return True
    
    def get_answer_sequence_list(self, question_id) :
        query = '''
            SELECT answer_sequence_list FROM questions WHERE question_id = %s
        '''
        self.db_cursor.execute(query, (question_id,))
        answer_sequence = self.db_cursor.fetchone()[0]
        # LOG.debug(f'Get answer list: [{answer_sequence}]')
        if len(answer_sequence.strip()) >= 2:
            answer_list = answer_sequence.split(',')
            try:
                answer_list = list(map(int, answer_list))
                return answer_list
            except Exception as e:
                LOG.error(f"Fail to unpack answer list, {answer_sequence}")
                return None
        else:
            return None        
    
    def get_user_question_and_answer(self):
        query = '''
            SELECT recent_question_id, last_answer_id FROM users WHERE user_id = %s
        '''
        self.db_cursor.execute(query, (self.user_id,))
        user_info = self.db_cursor.fetchone()
        recent_question_id = user_info[0]
        last_answer_id = user_info[1]        
        return recent_question_id, last_answer_id
        
    def update_user_last_answer_id(self, last_answer_id):
        query = '''
            UPDATE users
            SET last_answer_id = %s
            WHERE user_id = %s
        '''
        self.execute_query(query, (last_answer_id, self.user_id,))
        LOG.info(f"User {self.user_id} last_answer_id updated to {last_answer_id}.")


    # 更新用户的max_answer_count
    def update_limit(self, limit):
        query = '''
            UPDATE users
            SET max_answer_count = %s
            WHERE user_id = %s
        '''
        self.execute_query(query, (limit, self.user_id,))
        LOG.info(f"Set limit to {limit}")

    def lookup_history(self):
        # query = '''
        #     SELECT question_id, question_content, answer_sequence_list 
        #     FROM (
        #         SELECT question_id, question_content, MAX(question_time) as latest_time, answer_sequence_list
        #         FROM questions 
        #         WHERE user_id = %s
        #         GROUP BY question_content 
        #         ORDER BY latest_time DESC
        #     ) AS subquery 
        #     LIMIT 10;
        #     '''
        query = '''
            SELECT q.question_id, q.question_content, q.answer_sequence_list 
            FROM questions q
            JOIN (
                SELECT question_content, MAX(question_time) as latest_time
                FROM questions 
                WHERE user_id = %s
                GROUP BY question_content 
            ) subquery ON q.question_content = subquery.question_content AND q.question_time = subquery.latest_time
            WHERE q.user_id = %s
            ORDER BY q.question_time DESC
            LIMIT 10;
        '''
        self.execute_query(query, (self.user_id,self.user_id,))
        results = self.db_cursor.fetchall()

        result_str = ''
        for row in results:
            id, content, answer_str = row
            answer_list = answer_str.split(',')
            result_str += f"[{id}]: {content}。 {len(answer_list)}个参考答案。\n"

        return result_str 

    def lookup_chat_question(self, id) -> str:
        if self.user_id == str(Config.get_config_admin()):
            query = '''
                SELECT question, answer FROM chat_history 
                WHERE ID=%s
                '''
            
            self.execute_query(query, (id,))
        else:
            query = '''
                SELECT question, answer FROM chat_history 
                WHERE ID=%s AND user_id=%s
                '''
            
            self.execute_query(query, (id, self.user_id,))
        result = self.db_cursor.fetchone()
        if result:
            return f'{id}、【Q】{result[0]}\n【A】{result[1]}'
        else:
            return f"Question {id} 不存在或您没有权限查看"
        
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
    
    def lookup_chat_history(self) -> str:
        # query = '''
        #     SELECT id, question, answer 
        #     FROM (
        #         SELECT id, question, MAX(time) as latest_time, answer
        #         FROM chat_history 
        #         WHERE user_id = ? 
        #         GROUP BY question 
        #         ORDER BY latest_time DESC
        #     ) AS subquery 
        #     LIMIT 10;
        #     '''
        if self.user_id == str(Config.get_config_admin()):
            query = '''
                SELECT ch.id, ch.question, ch.answer 
                FROM chat_history ch
                JOIN (
                    SELECT question, MAX(time) as latest_time
                    FROM chat_history                     
                    GROUP BY question 
                ) subquery ON ch.question = subquery.question AND ch.time = subquery.latest_time
                ORDER BY ch.time DESC
                LIMIT 10;
            '''
            self.execute_query(query, ())
        else:
            query = '''
                SELECT ch.id, ch.question, ch.answer 
                FROM chat_history ch
                JOIN (
                    SELECT question, MAX(time) as latest_time
                    FROM chat_history 
                    WHERE user_id = %s
                    GROUP BY question 
                ) subquery ON ch.question = subquery.question AND ch.time = subquery.latest_time
                WHERE ch.user_id = %s
                ORDER BY ch.time DESC
                LIMIT 10;
            '''
            self.execute_query(query, (self.user_id,self.user_id,))
        results = self.db_cursor.fetchall()

        result_str = ''
        for row in results:
            id, question, answer = row
            # answer_list = answer_str.split(',')
            result_str += f"{id}、【问题】{question[:100]}。。。。。。\n【答案】{answer[:100]} 。。。。。。\n"
            result_str += '--'*30 + '\n'


        return result_str 

    def position_history_question(self, question_id):
        if question_id == -1:
            # query = '''
            #     SELECT question_id, question_content 
            #     FROM (
            #         SELECT question_id, question_content, MAX(question_time) as latest_time 
            #         FROM questions 
            #         WHERE user_id = ? 
            #         GROUP BY question_content 
            #         ORDER BY latest_time DESC
            #     ) AS subquery 
            #     LIMIT 1;
            #     '''
            query = '''
                SELECT q.question_id, q.user_id, q.question_content, q.answer_sequence_list, q.question_time
                FROM (
                    SELECT DISTINCT question_content
                    FROM questions
                    WHERE 
                        user_id = %s
                        AND answer_sequence_list IS NOT NULL 
                        AND CHAR_LENGTH(answer_sequence_list) > 2
                ) AS subquery
                JOIN questions AS q
                ON subquery.question_content = q.question_content
                ORDER BY q.question_time DESC
                LIMIT 1;    
            '''
            self.execute_query(query, (self.user_id,))

            results = self.db_cursor.fetchone()            
            question_id, uid, content, answer, qtime = results
            LOG.info(f"Find {question_id} ({content}) ({qtime}) for -1")   
            self.update_user_recent_question_id(question_id)
            return True, content
        else:
            query = '''
                SELECT question_id, user_id 
                FROM questions WHERE question_id=%s
            '''
            self.execute_query(query, (question_id,))
            results = self.db_cursor.fetchone()
            if results:
                if results[1] == self.user_id:
                    self.update_user_recent_question_id(question_id)
                    return True, ""
                else:
                    return False, ""
            else:
                return False, ""

    def create_answer_title(self, answer_list):        
        sum1 = sum2 = 0
        for i in answer_list:
            if i > 1000000:
                sum1 += 1
            else:
                sum2 += 1
        result = f'找到{len(answer_list)}个答案，包括{sum1}篇参考文章，{sum2}个参考知识点'
        # if self.get_user_optflg():
        #     result += ", 和1个来自大模型的答案"

        return result
    def debug_get_user_info(self, eid) -> str:
        query = '''
            SELECT name, sub_company FROM employee WHERE employee_id = %s
            '''
        self.execute_query(query, (eid,))
        result = self.db_cursor.fetchone()
        if result:
            name = result[0]
            sub_comp = result[1]
            res_str = self.get_user_info(eid)
            res_str += f', 姓名:{name}, 所属公司:{sub_comp}'
            return res_str
        else:
            return f"没有发现员工号为{eid}的员工"
        
    def get_token_price(self):
        number_token = self.get_user_number_token()
        permission = self.get_user_chat_permission()
        if permission == CONST.CHAT_LEVEL_E4:
            s = "{:.2f}".format(number_token*Config.get_config_ERNIE4_price()/1000)
        else:
            s = "{:.2f}".format(number_token*Config.get_config_ERNIE3_price()/1000)
        return number_token, s
    
    def get_user_info(self, eid=None) -> str:
        query = '''
            SELECT recent_question_id, last_answer_id, max_answer_count, summaryflag, mobileflag, chat_flag, token, chat_permission 
            FROM users WHERE user_id = %s 
        
            '''
        search_id = self.user_id if eid is None else eid 

        self.execute_query(query, (search_id,))  
        result = self.db_cursor.fetchone()
        if result:
            recent_question_id, last_answer_id, max_answer_count, summaryflag, mobileflag, chat_flag, token, chat_permission = result 
            res_str = f'你好 {search_id}, 最近问题ID:{recent_question_id}, 上次答案ID:{last_answer_id}, 最大回答数:{max_answer_count}, '
            res_str += '摘要模式:' + ('打开' if summaryflag != 0 else '关闭') + ', '
            res_str += '移动模式:' + ('打开' if mobileflag != 0 else '关闭') + ', '
            res_str += 'chat模式:' + ('打开' if chat_flag != 0 else '关闭') + ', '
            res_str += f'Token:{token}, '
            res_str += 'chat权限:' 

            chat_levels = {
                CONST.CHAT_LEVEL_E3: '文心一言3.5',
                CONST.CHAT_LEVEL_E4: '文心一言4.0'
            }
            
            res_str += chat_levels.get(chat_permission, '无')
            return res_str
        else:
            return '无用户信息'
        
    def fetch_answer(self):
        recent_question_id, last_answer_id = self.get_user_question_and_answer()
        answer_list = self.get_answer_sequence_list(recent_question_id)

        if answer_list == None:
            # no answer from knowledgebase        
            if self.get_user_optflg():
                # get answer from LLM
                query = '''
                    SELECT llm_answer FROM questions WHERE question_id = %s
                    '''
                self.execute_query(query, (recent_question_id, ))
                result = self.db_cursor.fetchone()[0]
                if len(result.strip()) > 0:
                    row_string = f'【来自大模型的答案】：' + result
                else:
                    row_string = CONST.NO_FINDING
                
                self.update_user_last_answer_id(last_answer_id+1)
                LOG.info(f"Return answers: {row_string}")
                return row_string
            else: 
                result_str = CONST.NO_FINDING
                LOG.info(f"Return answers: {result_str}")
                return result_str

        query = '''
            SELECT tp.id, tp.content, kb.name, kb.full_path, kb.URL
            FROM textpoints_1204 AS tp
            JOIN knowledgebase AS kb ON tp.wiki_id = kb.ID
            WHERE tp.id = %s
        '''

        query1 = '''
            SELECT id, name, description, full_path, URL FROM knowledgebase
            WHERE id=%s
            '''
        
        total_length = 0
        result_str = ''
        number_answers = 1

        LOG.info(f"last_answer_id = {last_answer_id}, length of answer_list is {len(answer_list)}")   
                
        if last_answer_id >= len(answer_list):
            row_string = "没有更多的答案了"

            if last_answer_id == len(answer_list)+1 and self.get_user_optflg():
                query = '''
                    SELECT llm_answer FROM questions WHERE question_id = %s
                    '''
                self.execute_query(query, (recent_question_id, ))
                result = self.db_cursor.fetchone()[0]
                if len(result.strip()) > 0:
                    row_string = f'【来自大模型的答案】：' + result
                
                self.update_user_last_answer_id(last_answer_id+1)
                return row_string
            else:
                return row_string
        
        i = last_answer_id
        end_pos = len(answer_list)-1

        HREF = '''<a href="{}" target="_blan">{}</a>'''
        while i<=end_pos:                   

            if i==0:
                # before the first answer, provide the title
                answer_title = self.create_answer_title(answer_list)
                LOG.debug(f"Get answer title: {answer_title}")
                first_answer_flag = True
            else:
                first_answer_flag = False 
                answer_title = ''

            summary_flag = False
            if answer_list[i] > 1000000:
                wiki_id = str(answer_list[i])
                LOG.debug(f"Look for summary: {wiki_id}")
                self.execute_query(query1, (wiki_id,))
                summary_flag = True
            else:    
                self.execute_query(query, (answer_list[i],))  

            row =self.db_cursor.fetchone() 

            prefix_str = ''
            if summary_flag:
                id, name, content, full_path, URL = row
                prefix_str = '摘要'                
            else:
                id, content, name, full_path, URL = row
                content = self.replace_markdown_link_with_html(content)

            if self.get_user_mobile_flag():
                href_str = HREF.format(URL, full_path)                
            else:
                href_str = HREF.format(URL, name)

            row_string = f'{answer_title}\n【{prefix_str}参考#{i+1}】【出处：{href_str}】' + content 

            utf8_bytes = row_string.encode('utf-8') 
            byte_length = len(utf8_bytes)   
            LOG.info(f"length in bytes of answer#{i} is {byte_length}, total length so far is {total_length}")            

            if number_answers == 1:  # this is the first answer in this batch
                if len(utf8_bytes) > self.length_limit: 
                    # just return this one, shortened
                    href_str = HREF.format(URL, name)
                    row_string = f'【{prefix_str}参考#{i+1}】【出处：{href_str}】' + content[0:625] + "......"                    
                    result_str = row_string                   
                    self.update_user_last_answer_id(i+1)
                    LOG.info(f"Just return one answer: {result_str[:80]}")
                    return result_str                
                result_str = row_string + "\n"
                total_length += byte_length
                number_answers += 1
            else: # this is the 2nd or following answer in this batch
                if total_length + byte_length > self.length_limit:  # could not add more answers
                    result_str += "\t未完待续..."
                    self.update_user_last_answer_id(i)
                    LOG.info(f"Could not add more answers: {result_str}")
                    return result_str
                else: # append more answers
                    result_str += row_string + "\n"
                    total_length += byte_length
                    number_answers += 1
            i += 1

        self.update_user_last_answer_id(i+1)
        LOG.info(f"Return answers: {result_str}")
        return result_str
    
    def debug_get_userlist(self):
        query = '''
            SELECT DISTINCT user_id from users'''
        self.execute_query(query)
        results = self.db_cursor.fetchall()
        result_str = f'Total number of users in system is {len(results) }: '
        for item in results:
            result_str += item[0] + ', '
        
        return result_str
    
    def debug_get_question_number(self):
        query = '''
            SELECT COUNT(*) FROM questions'''
        self.execute_query(query)
        return f"number of questions so far is {self.db_cursor.fetchone()[0]}"
    
    def debug_get_last_chat_questions(self, number):
        query = '''
            SELECT q.id, q.user_id, q.question, q.answer, q.time
            FROM (
                SELECT DISTINCT question
                FROM chat_history
                WHERE 
                    answer IS NOT NULL 
                    AND CHAR_LENGTH(answer) > 10
            ) AS subquery
            JOIN chat_history AS q
            ON subquery.question = q.question
            ORDER BY q.time DESC
            LIMIT %s;
            '''
        self.execute_query(query, (number, ))
        results = self.db_cursor.fetchall()

        result_str = ''
        for row in results:
            id, user_id, content, answer, qtime = row
            # query = '''
            #     SELECT user_id, question_time FROM questions WHERE question_id=%s'''
            # self.execute_query(query, (id,))
            # user, qtime = self.db_cursor.fetchone()        
            result_str += f"[{id}]:[{user_id}]:[{qtime}]({content})\n"

        return result_str 

    def debug_get_last_questions(self, number):
        query = '''
            SELECT q.question_id, q.user_id, q.question_content, q.answer_sequence_list, q.question_time
            FROM (
                SELECT DISTINCT question_content
                FROM questions
                WHERE 
                    answer_sequence_list IS NOT NULL 
                    AND CHAR_LENGTH(answer_sequence_list) > 2
            ) AS subquery
            JOIN questions AS q
            ON subquery.question_content = q.question_content
            ORDER BY q.question_time DESC
            LIMIT %s;
            '''
        self.execute_query(query, (number, ))
        results = self.db_cursor.fetchall()

        result_str = ''
        for row in results:
            id, user_id, content, answer_list, qtime = row
            # query = '''
            #     SELECT user_id, question_time FROM questions WHERE question_id=%s'''
            # self.execute_query(query, (id,))
            # user, qtime = self.db_cursor.fetchone()        
            result_str += f"[{id}]:[{user_id}]:[{qtime}]({content})\n"

        return result_str 
    
    # def get_all_wiki(self) -> list:
    #     query = ''' SELECT id, name, parent_wiki_id FROM knowledgebase '''
    #     self.execute_query(query, ())
    #     return self.db_cursor.fetchall()

    # def insert_wiki_data(self, id, name, description, markdown_description, parent_wiki_id, index) :
    #     sha_digest = generate_sha_digest(markdown_description)
    
    #     # cursor.execute('SELECT id, finger_print FROM knowledgebase WHERE finger_print=?', (sha_digest,))
    #     # existing_row = cursor.fetchone()
    #     query = '''
    #         SELECT id, finger_print FROM knowledgebase WHERE id = %s
    #         '''
    #     self.execute_query(query, (id,))        
    #     existing_row_id = self.db_cursor.fetchone()
    
    #     debug_str = ""
    #     if existing_row_id is not None:
    #         if existing_row_id[1] == sha_digest:
    #             LOG.debug(f"{index}: {id}:{name}, already exists and content is the same")
    #         return False
    #     else:
    #         debug_str = f"{index}: {id}:{name}, already exists, content needs to update"
    #         query = '''
    #             DELETE FROM knowledgebase WHERE id = %s
    #             '''
    #         self.execute_query(query, (id,))           
            
    #     url_string = f"https://www.tapd.cn/{workspace_id}/markdown_wikis/show/#{id}"
    #     query = '''
    #         INSERT INTO knowledgebase (id, name, description, markdown_description, parent_wiki_id, need_flag, finger_print,url)
    #         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    #         '''
    #     self.execute_query(query,(id, name, description[:20000], markdown_description[:20000], parent_wiki_id, 0, sha_digest, url_string,)) 
        
    #     if len(debug_str) == 0:
    #         LOG.info(f"{index}: {id}:{name} is inserted")
    #     else:
    #         debug_str += ", done"
    #         LOG.info(debug_str)
    #     return True

    
    


    
