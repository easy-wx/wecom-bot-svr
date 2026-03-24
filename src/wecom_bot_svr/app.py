import inspect
import logging
import os
import queue
import threading
import xml.etree.cElementTree as ET

import requests
from flask import Flask, request
from wx_crypt import WXBizMsgCrypt, WxChannel_Wecom

from .req_msg import ReqMsg
from .rsp_msg import RspTextMsg, rsp_msg_from_active_params


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
    """_message_handler 在后台线程执行；同步回包最多等待 FIRST_HANDLER_RSP_TIMEOUT_SEC 秒（含「等 handler 返回」与「生成器首条 yield」）。超时则空回包，结果改为主动推送。注意 handler 内勿依赖 Flask 的 request 线程局部变量。"""
    FIRST_HANDLER_RSP_TIMEOUT_SEC = 4

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

        p = request.values
        rsp = rsp_msg_from_active_params(p)
        if rsp is None:
            return "Invalid msg_type"
        send_ret = self.send_active_message(p.get("chat_id"), rsp)
        return "发送消息结果：" + send_ret

    def send_active_message(self, chat_id, rsp_msg):
        """按 Rsp* 主动发送，与 handler 返回类型一致。"""
        if not chat_id:
            return "缺少 chat_id"
        if rsp_msg is None:
            return "缺少消息"
        mt = rsp_msg.msg_type
        if mt == "file":
            if rsp_msg.file_path:
                return self.send_file(chat_id, rsp_msg.file_path)
            if rsp_msg.media_id:
                return self.proactively_send(chat_id, "file", "文件", {"file": {"media_id": rsp_msg.media_id}})
            return "文件消息缺少 file_path 或 media_id"
        if mt == "markdown":
            body = rsp_msg.content if rsp_msg.content is not None else ""
            return self.send_markdown(chat_id, body)
        if mt == "text":
            text = rsp_msg.content if rsp_msg.content is not None else ""
            return self.send_text(
                chat_id,
                text,
                mentioned_list=rsp_msg.mentioned_list,
                mentioned_mobile_list=rsp_msg.mentioned_mobile_list,
            )
        if mt == "image":
            return self.send_encoded_image(
                chat_id,
                rsp_msg.base64_image_data,
                rsp_msg.md5,
            )
        if mt == "news":
            return self.send_news(
                chat_id,
                rsp_msg.title,
                rsp_msg.description,
                rsp_msg.url,
                rsp_msg.pic_url,
            )
        return "Invalid msg_type"

    def _empty_sync_rsp(self):
        r = RspTextMsg()
        r.content = ""
        return r

    def _dispatch_message_handler_with_timeout(self, msg):
        """在后台执行 _message_handler，首包（返回体或生成器首条）超过 FIRST_HANDLER_RSP_TIMEOUT_SEC 则空回包并改主动推送。"""
        chat_id = msg.chat_id
        out = queue.Queue(maxsize=1)

        def worker():
            try:
                if len(inspect.signature(self._message_handler).parameters) == 2:
                    raw = self._message_handler(msg, self)
                else:
                    raw = self._message_handler(msg)
                out.put((True, raw))
            except Exception:
                self.logger.exception("message handler failed")
                out.put((False, None))

        threading.Thread(target=worker, daemon=True).start()

        try:
            ok, raw = out.get(timeout=self.FIRST_HANDLER_RSP_TIMEOUT_SEC)
        except queue.Empty:

            def on_late():
                ok_late, raw_late = out.get()
                if not ok_late:
                    return
                if inspect.isgenerator(raw_late):
                    try:
                        for item in raw_late:
                            if item is None:
                                continue
                            send_ret = self.send_active_message(chat_id, item)
                            if send_ret == "Invalid msg_type":
                                self.logger.warning(
                                    "send_active_message: unsupported msg_type %s",
                                    item.msg_type)
                    except Exception:
                        self.logger.exception("message handler generator failed")
                else:
                    self.send_active_message(chat_id, raw_late)

            threading.Thread(target=on_late, daemon=True).start()
            return self._empty_sync_rsp()

        if not ok:
            return self._empty_sync_rsp()

        if inspect.isgenerator(raw):
            self.logger.info(
                "_dispatch_message_handler_with_timeout: handler returned generator, chat_id=%s",
                chat_id,
            )
            return self._handle_message_handler_generator(msg, raw)
        return raw

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
            rsp_msg = self._dispatch_message_handler_with_timeout(msg)

        nonce = params.get("nonce")
        ret, rsp = wx_cpt.EncryptMsg(rsp_msg.dump_xml(), nonce, timestamp)
        if ret != 0:
            print("err: encrypt fail: " + str(ret))
        return rsp

    def _handle_message_handler_generator(self, msg, gen):
        chat_id = msg.chat_id
        q = queue.Queue()
        done = object()

        def producer():
            put_idx = 0
            try:
                for rsp in gen:
                    put_idx += 1
                    c = getattr(rsp, "content", None)
                    self.logger.info(
                        "generator producer put #%s chat_id=%s content=%r",
                        put_idx,
                        chat_id,
                        c,
                    )
                    q.put(rsp)
            except Exception:
                self.logger.exception(
                    "message handler generator failed after %s puts", put_idx
                )
            finally:
                self.logger.info(
                    "generator producer finally: sentinel done after %s item(s)", put_idx
                )
                q.put(done)

        def drain():
            send_idx = 0
            while True:
                item = q.get()
                if item is done:
                    self.logger.info(
                        "generator drain: got sentinel, send_active_message calls=%s",
                        send_idx,
                    )
                    break
                if item is not None:
                    send_idx += 1
                    c = getattr(item, "content", None)
                    self.logger.info(
                        "generator drain send_active_message #%s chat_id=%s content=%r",
                        send_idx,
                        chat_id,
                        c,
                    )
                    send_ret = self.send_active_message(chat_id, item)
                    self.logger.info(
                        "generator drain send_active_message #%s result=%r", send_idx, send_ret
                    )
                    if send_ret == "Invalid msg_type":
                        self.logger.warning(
                            "send_active_message: unsupported msg_type %s", item.msg_type)

        threading.Thread(target=producer, daemon=True).start()

        try:
            first = q.get(timeout=self.FIRST_HANDLER_RSP_TIMEOUT_SEC)
        except queue.Empty:
            first = None

        if first is None:
            self.logger.info(
                "generator first wait: timeout (>%ss), empty sync rsp + drain all via proactive",
                self.FIRST_HANDLER_RSP_TIMEOUT_SEC,
            )
            threading.Thread(target=drain, daemon=True).start()
            return self._empty_sync_rsp()
        if first is done:
            self.logger.info("generator first wait: empty generator (done sentinel)")
            return self._empty_sync_rsp()
        if first.msg_type == 'file':
            send_ret = self.send_file(chat_id, first.file_path)
            if send_ret == "上传文件失败":
                return self._empty_sync_rsp()
            return self._empty_sync_rsp()

        self.logger.info(
            "generator first wait: sync reply content=%r, drain rest via proactive",
            getattr(first, "content", None),
        )
        threading.Thread(target=drain, daemon=True).start()
        return first

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
            self.logger.warning(
                "proactively_send %s failed status=%s body=%s, payload=%s",
                msg_type_name,
                r.status_code,
                r.text[:500] if r.text else "",
                payload,
            )
            return f"发送{msg_type_name}失败"
        except Exception:
            self.logger.exception("proactively_send %s exception", msg_type_name)
            return f"发送{msg_type_name}失败"

    def send_file(self, chat_id, file_path):
        media_id = self.upload_file(file_path)
        if media_id is None:
            return "上传文件失败"
        self.logger.info(f"上传文件成功 media_id={media_id}")
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
