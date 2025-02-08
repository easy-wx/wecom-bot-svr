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
    def __init__(self, name, host, port, path, token=None, aes_key=None, corp_id=None, bot_key=None,
                 active_msg_path="/active_send"):
        """
        :param name:
        :param host:
        :param port:
        :param path:
        :param token:
        :param aes_key:
        :param corp_id:
        :param bot_key:
        :param active_msg_path: 主动发送消息的路径
        """
        self.host = host
        self.port = port
        self.path = path
        self.active_msg_path = active_msg_path
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
        self._app.post(self.active_msg_path)(self.handle_active_send)
        self._app.run(host=self.host, port=self.port)

    def handle_active_send(self):
        # 避免外网直接访问：判断来源IP如果非本地地址，直接返回
        if request.remote_addr != "127.0.0.1":
            return "Invalid request"

        # 获取请求参数
        params = request.values
        msg_type = params.get("msg_type")
        chat_id = params.get("chat_id")
        if msg_type == "file":
            file_path = params.get("file_path")
            send_ret = self.send_file(chat_id, file_path)
        elif msg_type == "markdown":
            content = params.get("content")
            send_ret = self.send_markdown(chat_id, content)
        elif msg_type == "text":
            content = params.get("content")
            send_ret = self.send_text(chat_id, content)
        elif msg_type == "image":
            base64_image_data = params.get("base64_image_data")
            md5 = params.get("md5")
            send_ret = self.send_encoded_image(chat_id, base64_image_data, md5)
        elif msg_type == "news":
            title = params.get("title")
            description = params.get("description")
            url = params.get("url")
            pic_url = params.get("pic_url")
            send_ret = self.send_news(chat_id, title, description, url, pic_url)
        else:
            return "Invalid msg_type"

        return "发送消息结果：" + send_ret

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

    def upload_file(self, file_path):
        filename = os.path.basename(file_path)
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

    def proactively_send(self, chat_id, msg_type, msg_type_name, msg_data):
        """"""
        try:
            payload = {
                "chatid": chat_id,
                "msgtype": msg_type,
            }
            payload.update(msg_data)

            r = requests.post(url=f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self._bot_key}',
                              json=payload)
            if r.status_code == 200 and r.json().get("errcode") == 0:
                return f"发送{msg_type_name}成功"
            else:
                return f"发送{msg_type_name}失败"
        except:
            return f"发送{msg_type_name}失败"

    def send_file(self, chat_id, file_path):
        media_id = self.upload_file(file_path)
        if media_id is None:
            return "上传文件失败"

        return self.proactively_send(chat_id, "file", "文件", {"file": {"media_id": media_id}})

    def send_markdown(self, chat_id, content):
        return self.proactively_send(chat_id, "markdown", "Markdown", {"markdown": {"content": content}})

    def send_text(self, chat_id, content, mentioned_list=None, mentioned_mobile_list=None):
        msg_data = {
            "text": {
                "content": content,
            }
        }
        if mentioned_list is not None:
            msg_data["text"]["mentioned_list"] = mentioned_list
        if mentioned_mobile_list is not None:
            msg_data["text"]["mentioned_mobile_list"] = mentioned_mobile_list
        return self.proactively_send(chat_id, "text", "文本", msg_data)

    def send_encoded_image(self, chat_id, base64_image_data, md5):
        return self.proactively_send(chat_id, "image", "图片", {"image": {"base64": base64_image_data, "md5": md5}})

    def send_news(self, chat_id, title, description, url, pic_url):
        return self.proactively_send(chat_id, "news", "图文", {"news": {"articles": [
            {
                "title": title,
                "description": description,
                "url": url,
                "picurl": pic_url
            }
        ]}})
