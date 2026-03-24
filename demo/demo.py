import base64
import hashlib
import logging
import re
import sys
import time

from wecom_bot_svr import (
    WecomBotServer,
    RspFileMsg,
    RspImageMsg,    
    RspMarkdownMsg,
    RspNewsMsg,
    RspTextMsg,
    ReqMsg,
)
from wecom_bot_svr.req_msg import TextReqMsg

_demo_log = logging.getLogger(__name__)

# 1×1 PNG，用于 full_media_test 图片类型（企业微信要求 base64 + md5）
_FULL_MEDIA_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_FULL_MEDIA_PNG_MD5 = hashlib.md5(base64.b64decode(_FULL_MEDIA_PNG_B64)).hexdigest()


def help_md():
    return """### Help 列表
- [给项目点赞](https://github.com/easy-wx/wecom-bot-svr)
- `sleep N`：休眠 N 秒后回复（演示回调超时与主动推送）
- `repeat N`：连续推送 N 条，内容为 `msg 1/N` … `msg N/N`（演示生成器）
- `full_media_test`：生成器依次推送 text / markdown / file / news（演示各 Rsp* 类型）
- 其他功能请自行开发
"""


def msg_handler(req_msg: ReqMsg, server: WecomBotServer):
    # @机器人 help 打印帮助信息
    if req_msg.msg_type == 'text' and isinstance(req_msg, TextReqMsg):
        stripped = req_msg.content.strip()
        if stripped == 'help':
            ret = RspMarkdownMsg()
            ret.content = help_md()
            return ret
        m_sleep = re.match(r'(?i)sleep\s+(\d+)\s*$', stripped)
        if m_sleep:
            n = int(m_sleep.group(1))
            time.sleep(n)
            ret = RspTextMsg()
            ret.content = f'message after sleep {n}s done'
            return ret
        m_repeat = re.match(r'(?i)repeat\s+(\d+)\s*$', stripped)
        if m_repeat:
            n = int(m_repeat.group(1))

            def repeat_gen():
                _demo_log.info("repeat_gen start n=%s", n)
                for i in range(1, n + 1):
                    _demo_log.info("repeat_gen before yield i=%s/%s", i, n)
                    r = RspTextMsg()
                    r.content = f'msg {i}/{n}'
                    yield r
                    _demo_log.info("repeat_gen after yield i=%s/%s (consumer resumed)", i, n)
                _demo_log.info("repeat_gen finished normally, total yields=%s", n)

            return repeat_gen()
        elif stripped == 'full_media_test':

            def full_media_test_gen():
                r1 = RspTextMsg()
                r1.content = "[full_media_test 4-1] text"
                yield r1
                sleep_N = 1  
                time.sleep(sleep_N)
                r2 = RspMarkdownMsg()
                r2.content = "### [full_media_test 4-2] markdown\n- line"
                yield r2
                time.sleep(sleep_N)
                r3 = RspFileMsg()
                r3.file_path = "full_media_test_4-3.txt"
                with open(r3.file_path, "w") as f:
                    f.write("This is a test file. Welcome to star easy-wx/wecom-bot-svr!")
                yield r3
                time.sleep(sleep_N)
                r4 = RspNewsMsg()
                r4.title = "[full_media_test 4-4] news"
                r4.description = "full_media_test news body"
                r4.url = "https://github.com/easy-wx/wecom-bot-svr"
                r4.pic_url = "https://open.weixin.qq.com/zh_CN/htmledition/res/assets/res-design-download/icon64_wx_logo.png"
                yield r4


            return full_media_test_gen()

        elif stripped == 'give me a file' and server is not None:
            # 生成文件、发送文件可以新启线程异步处理
            with open('output.txt', 'w') as f:
                f.write("This is a test file. Welcome to star easy-wx/wecom-bot-svr!")
            server.send_file(req_msg.chat_id, 'output.txt')
            return RspTextMsg()  # 不发送消息，只回复文件
        

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
    bot_key = 'xxxxx'  # 机器人配置中的webhook key

    # 这里要跟机器人名字一样，用于切分群组聊天中的@消息
    bot_name = 'jasonzxpan-test'
    server = WecomBotServer(bot_name, host, port, path='/wecom_bot', token=token, aes_key=aes_key, corp_id=corp_id,
                            bot_key=bot_key)

    server.set_message_handler(msg_handler)
    server.set_event_handler(event_handler)
    server.run()


if __name__ == '__main__':
    main()
