import os
from flask import Flask, request

from .WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ET


# 参考文档：https://km.woa.com/articles/show/387107?kmref=search&from_page=1&no=2#10128

class UserInfo(object):
    def __init__(self, en_name, cn_name, user_id, chat_id=None):
        self.en_name = en_name
        self.cn_name = cn_name
        self.user_id = user_id
        self.chat_id = chat_id


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
    def __init__(self, name, host, port, path="/wx_bot_cb", token=None, aes_key=None, corp_id=None):
        self.host = host
        self.port = port
        self.path = path
        self._token = token if token is not None else os.getenv("WX_BOT_TOKEN")
        self._aes_key = aes_key if aes_key is not None else os.getenv("WX_BOT_AES_KEY")
        self._corp_id = corp_id if corp_id is not None else os.getenv("WX_BOT_CORP_ID")
        self._app = Flask(name)
        self._message_handler = None
        self._event_handler = None
        self._error_handler = None

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
        return WXBizMsgCrypt(self._token, self._aes_key, self._corp_id)

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
        print(msg)
        if ret != 0:
            if self._error_handler:
                self._error_handler(ret)
            else:
                return None
            # 获取所有的查询参数

        # 解密后的数据是xml格式，用python的标准库xml.etree.cElementTree可以解析
        xml_tree = ET.fromstring(msg)
        user = xml_tree.find('From')
        user_info = UserInfo(user.find('Alias').text, user.find('Name').text, user.find('UserId').text)
        msg_type = xml_tree.find('MsgType').text
        if msg_type == 'event':
            event_type = xml_tree.find('Event').find('EventType').text
            rsp_str = self._event_handler(user_info, event_type, xml_tree)
        elif msg_type == 'text':
            content = xml_tree.find('Text').find('Content').text
            if xml_tree.find("ChatType").text == "group":
                content = content.replace("@ugc", "").strip()
            chat_id = xml_tree.find("ChatId").text
            if chat_id:
                user_info.chat_id = chat_id
            rsp_str = self._message_handler(user_info, msg_type, content, xml_tree)
        else:
            rsp_str = ""
        return _encode_rsp(wx_cpt, rsp_str)
