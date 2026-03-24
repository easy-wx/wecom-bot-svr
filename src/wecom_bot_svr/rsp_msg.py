import json
import xml.etree.cElementTree as ET

# https://developer.work.weixin.qq.com/document/path/99399#%E5%8A%A0%E5%AF%86%E4%B8%8E%E5%9B%9E%E5%A4%8D

class RspMsg(object):
    def __init__(self):
        self.msg_type = None
        self.visible_to_user = None
        self.xml_tree = ET.Element('xml')

    def insert_elem(self, name, value):
        curr_node = self.xml_tree

        for n in name.split('/'):
            if curr_node.find(n) is None:
                e = ET.Element(n)
                curr_node.append(e)
            curr_node = curr_node.find(n)
        curr_node.text = value

    def dump_xml(self):
        self.update_xml()
        return ET.tostring(self.xml_tree, encoding='ascii', method='html')

    def update_xml(self):
        self.insert_elem("MsgType", self.msg_type)
        if self.visible_to_user is not None:
            self.insert_elem("VisibleToUser", "|".join([str(x) for x in self.visible_to_user]))


class RspTextMsg(RspMsg):
    def __init__(self):
        super().__init__()
        self.msg_type = 'text'
        self.content = None
        # 主动推送 webhook 时传给 send_text；同步回调 XML 仍只写 Content
        self.mentioned_list = None
        self.mentioned_mobile_list = None

    def update_xml(self):
        super().update_xml()
        self.insert_elem('Text/Content', self.content)


class RspMarkdownMsg(RspMsg):
    def __init__(self):
        super().__init__()
        self.msg_type = 'markdown'
        self.content = None

    def update_xml(self):
        super().update_xml()
        self.insert_elem('Markdown/Content', self.content)


class RspFileMsg(RspMsg):
    """文件类：主动推送用 file_path（先上传再发）；若仅同步回调需自行填写 media_id。"""

    def __init__(self):
        super().__init__()
        self.msg_type = 'file'
        self.file_path = None
        self.media_id = None

    def update_xml(self):
        super().update_xml()
        mid = self.media_id if self.media_id is not None else ''
        self.insert_elem('File/MediaId', mid)


class RspImageMsg(RspMsg):
    """图片类，字段与 webhook send image 一致。"""

    def __init__(self):
        super().__init__()
        self.msg_type = 'image'
        self.base64_image_data = None
        self.md5 = None

    def update_xml(self):
        super().update_xml()
        self.insert_elem('Image/Base64', self.base64_image_data if self.base64_image_data is not None else '')
        self.insert_elem('Image/Md5', self.md5 if self.md5 is not None else '')


class RspNewsMsg(RspMsg):
    """图文类，单条 article，与 demo 中 send_news 一致。"""

    def __init__(self):
        super().__init__()
        self.msg_type = 'news'
        self.title = None
        self.description = None
        self.url = None
        self.pic_url = None

    def update_xml(self):
        super().update_xml()
        self.insert_elem('News/Articles/Item/Title', self.title if self.title is not None else '')
        self.insert_elem('News/Articles/Item/Description', self.description if self.description is not None else '')
        self.insert_elem('News/Articles/Item/Url', self.url if self.url is not None else '')
        self.insert_elem('News/Articles/Item/PicUrl', self.pic_url if self.pic_url is not None else '')


def _optional_json_list(val):
    """表单里的 mentioned_list 等：支持 JSON 数组字符串或已是 list。"""
    if val is None or val == "":
        return None
    if isinstance(val, (list, tuple)):
        return list(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            x = json.loads(s)
            if isinstance(x, list):
                return x
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def rsp_msg_from_active_params(p):
    """
    将主动发送接口（如 /active_send）的表单参数转为 Rsp* 消息，与 handler 返回类型一致。
    p 需实现 .get(key)；未知 msg_type 或缺少 msg_type 时返回 None。
    """
    if p is None:
        return None
    mt = p.get("msg_type")
    if not mt:
        return None
    if mt == "text":
        r = RspTextMsg()
        r.content = p.get("content")
        r.mentioned_list = _optional_json_list(p.get("mentioned_list"))
        r.mentioned_mobile_list = _optional_json_list(p.get("mentioned_mobile_list"))
        return r
    if mt == "markdown":
        r = RspMarkdownMsg()
        r.content = p.get("content")
        return r
    if mt == "file":
        r = RspFileMsg()
        r.file_path = p.get("file_path")
        r.media_id = p.get("media_id")
        return r
    if mt == "image":
        r = RspImageMsg()
        r.base64_image_data = p.get("base64_image_data")
        r.md5 = p.get("md5")
        return r
    if mt == "news":
        r = RspNewsMsg()
        r.title = p.get("title")
        r.description = p.get("description")
        r.url = p.get("url")
        r.pic_url = p.get("pic_url")
        return r
    return None


