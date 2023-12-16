import yaml

class ConfigReader:
    def __init__(self, file_path='config.yaml'):
        self.file_path = file_path
        self.config = self.read_config()

    def read_config(self):
        with open(self.file_path, 'r') as yaml_file:
            config_data = yaml.safe_load(yaml_file)
            return config_data

    def get_config_milvus_addr(self):
        return self.config.get('milvus', {})

    def get_config_optimize_flag(self):
        return self.config.get('optimize', {})
    
    def get_config_length(self):
        return self.config.get('wxlength', {})

    def get_config_API_KEY(self):
        return self.config.get('API_KEY', {})
    
    def get_config_threshold(self):
        return self.config.get('distance', {})

    def get_config_question_length_limit(self):
        return self.config.get('question_length', {})

    def get_config_timespan(self):
        return self.config.get('timespan', {})
    
    def get_config_debug_mode(self) -> bool:
        return self.config.get('debug_mode', {})
    
    def get_config_token_limit(self) -> int:
        return self.config.get('token_limit', {})
    
    def get_config_mysql_host(self) -> str:
        return self.config.get('mysql_host', {})
    def get_config_mysql_user(self) -> str:
        return self.config.get('mysql_user', {})
    def get_config_mysql_pwd(self) -> str:
        return self.config.get('mysql_pwd', {})
    def get_config_mysql_db(self) -> str:
        return self.config.get('mysql_db', {})
    
    def get_config_admin(self) -> str:
        return self.config.get('admin_user', {})
    
    def get_config_database_mode(self) -> str:
        return self.config.get('database', {})
    
    def get_config_ernie_api_key(self) -> str:
        return self.config.get('ERNIE_API_KEY', {})
    
    def get_config_ernie_secret_key(self) -> str:
        return self.config.get('ERNIE_SECRET_KEY', {})

    def get_config_ERNIE4_price(self) -> str:
        return self.config.get('e4_price', {})
    
    def get_config_ERNIE3_price(self) -> str:
        return self.config.get('e3_price', {})
    
    def get_config_maintenace(self) -> bool:
        if self.config.get("maintenance_mode", self) == 0:
            return False
        else:
            return True

Config = ConfigReader()