import logging
import sys

from wecom_bot_svr import app
from wecom_bot_svr.rsp_msg import RspTextMsg, RspMarkdownMsg


def help_md():
    return """### Help 列表
- [给项目点赞](https://github.com/easy-wx/wecom-bot-svr)
- 其他功能请自行开发
"""


def msg_handler(req_msg):
    # @机器人 help 打印帮助信息
    if req_msg.msg_type == 'text' and req_msg.content.strip() == 'help':
        ret = RspMarkdownMsg()
        ret.content = help_md()
        return ret

    # 返回消息类型
    ret = RspTextMsg()
    ret.content = f'msg_type: {req_msg.msg_type}'
    return ret


def event_handler(req_msg):
    ret = RspMarkdownMsg()
    if req_msg.event_type == 'add_to_chat':  # 入群事件处理
        ret.content = f'msg_type: {req_msg.msg_type}\n群会话ID: {req_msg.chat_id}\n查询用法请回复: help'
    return ret


def main():
    logging.basicConfig(stream=sys.stdout)
    logging.getLogger().setLevel(logging.INFO)

    token = 'xxx'  # 3个x
    aes_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'  # 43个x
    corp_id = ''
    host = '0.0.0.0'
    port = 5001
    # 这里要跟机器人名字一样，用于切分群组聊天中的@消息
    bot_name = 'jasonzxpan-test'
    server = app.WecomBotServer(bot_name, host, port, path='/wecom_bot', token=token, aes_key=aes_key, corp_id=corp_id)

    server.set_message_handler(msg_handler)
    server.set_event_handler(event_handler)
    server.run()


if __name__ == '__main__':
    main()
