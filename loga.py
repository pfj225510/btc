import logging
from logging.handlers import RotatingFileHandler

# 创建一个日志记录器
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.INFO)  # 设置日志记录级别

# 创建一个处理器，设置日志文件的大小和备份数量
handler = RotatingFileHandler(
    'app.log',  # 日志文件名
    maxBytes=1024 * 1024 * 100,  # 每个日志文件的最大字节数 (这里设置为1MB)
    backupCount=5  # 保留的备份文件数量
)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(handler)


def log(mess):
    logger.info(mess)
