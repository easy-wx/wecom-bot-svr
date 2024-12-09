import inspect
import logging
import os
import xml.etree.cElementTree as ET

import requests
from flask import Flask, request
from wx_crypt import WXBizMsgCrypt, WxChannel_Wecom

from .req_msg import ReqMsg


# 参考文档：https://km.woa.com/articles/show/387107?kmref=search&from_page=1&no=2#10128


def _encode_rsp(wx_cpt, rsp_str):
    xml = ET.Element('xml')
    ET.SubElement(xml, 'MsgType').text = 'markdown'
    markdown = ET.SubElement(xml, 'Markdown')
    ET.SubElement(markdown, 'Content').text = rsp_str
    plain = ET.tostring(xml).decode()

    # 加密消息
    params = request.args
    timestamp = params.get("timestamp")
    nonce = params.get("nonce")
    ret, rsp = wx_cpt.EncryptMsg(plain, nonce, timestamp)
    if ret != 0:
        print("err: encrypt fail: " + str(ret))
    return rsp


class WecomBotServer(object):
    def __init__(self, name, host, port, path, token=None, aes_key=None, corp_id=None, bot_key=None):
        self.host = host
        self.port = port
        self.path = path
        self._bot_key = bot_key if bot_key is not None else os.getenv("WX_BOT_KEY")
        self._token = token if token is not None else os.getenv("WX_BOT_TOKEN")
        self._aes_key = aes_key if aes_key is not None else os.getenv("WX_BOT_AES_KEY")
        self._corp_id = corp_id if corp_id is not None else os.getenv("WX_BOT_CORP_ID", default="")
        self._app = Flask(name)
        self._message_handler = None
        self._event_handler = None
        self._error_handler = None
        self.name = name
        self.logger = logging.getLogger()

    def set_message_handler(self, handler):
        self._message_handler = handler

    def set_event_handler(self, handler):
        self._event_handler = handler

    def set_error_handler(self, handler):
        self._error_handler = handler

    def set_flask_error_handler(self, handler):
        self._app.errorhandler(Exception)(handler)

    def run(self):
        if self._message_handler is None:
            raise Exception("message handler is not set")
        if self._event_handler is None:
            raise Exception("event handler is not set")
        self._app.get(self.path)(self.handle_bot_call_get)
        self._app.post(self.path)(self.handle_bot_call_post)
        self._app.run(host=self.host, port=self.port)

    def get_crypto_obj(self):
        return WXBizMsgCrypt(self._token, self._aes_key, self._corp_id, channel=WxChannel_Wecom)

    def handle_bot_call_get(self):
        # 获取请求参数
        params = request.args
        msg_signature = params.get("msg_signature")
        timestamp = params.get("timestamp")
        nonce = params.get("nonce")
        encrypted_echo_str = params.get("echostr")
        wx_cpt = self.get_crypto_obj()
        ret, decrypted_echo_str = wx_cpt.VerifyURL(msg_signature, timestamp, nonce, encrypted_echo_str)
        if ret != 0:
            return None
        return decrypted_echo_str

    def handle_bot_call_post(self):
        # 获取请求参数
        params = request.args
        msg_signature = params.get("msg_signature")
        timestamp = params.get("timestamp")
        nonce = params.get("nonce")
        wx_cpt = self.get_crypto_obj()

        # 解密出明文的echostr
        ret, msg = wx_cpt.DecryptMsg(request.data, msg_signature, timestamp, nonce)
        self.logger.info(f"decrypted msg: {msg.decode()}")
        if ret != 0:
            if self._error_handler:
                self._error_handler(ret)
            else:
                return None
            # 获取所有的查询参数

        # 解密后的数据是xml格式，用python的标准库xml.etree.cElementTree可以解析
        xml_tree = ET.fromstring(msg)
        msg = ReqMsg.create_msg(xml_tree)
        if msg.msg_type == 'event':
            rsp_msg = self._event_handler(msg)
        else:  # 消息
            if msg.msg_type == 'text' and msg.chat_type == 'group':
                msg.content = msg.content.replace(f"@{self.name}", "")
            if len(inspect.signature(self._message_handler).parameters) == 2:
                rsp_msg = self._message_handler(msg, self)
            else:  # 兼容旧版本
                rsp_msg = self._message_handler(msg)

        nonce = params.get("nonce")
        ret, rsp = wx_cpt.EncryptMsg(rsp_msg.dump_xml(), nonce, timestamp)
        if ret != 0:
            print("err: encrypt fail: " + str(ret))
        return rsp

    def upload_file(self, filename):
        # 文件路径
        file_path = 'output.csv'

        try:
            # 打开文件并上传
            with open(file_path, 'rb') as file:
                files = {'file': (filename, file)}
                response = requests.post(
                    url=f'https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={self._bot_key}&type=file',
                    files=files)
                # 检查响应
                if response.status_code != 200 and response.json().get("errcode") == 0:
                    return None
                return response.json()['media_id']
        except:
            return None

    def send_file(self, chat_id, file_path):
        media_id = self.upload_file(file_path)
        if media_id is None:
            return "上传文件失败"
        try:
            r = requests.post(
                url=f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self._bot_key}',
                json={
                    "chatid": chat_id,
                    "msgtype": "file",
                    "file": {
                        "media_id": media_id
                    }
                })
            if r.status_code == 200 and r.json().get("errcode") == 0:
                return "发送文件成功"
            else:
                return "发送文件失败"
        except:
            return "发送文件失败"
