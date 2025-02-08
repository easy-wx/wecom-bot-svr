# https://developer.work.weixin.qq.com/document/path/99399#%E8%A7%A3%E5%AF%86%E5%90%8E%E7%9A%84%E6%B6%88%E6%81%AF%E7%BB%93%E6%9E%84%E4%BD%93
class UserInfo(object):
    def __init__(self, en_name, cn_name, user_id):
        self.en_name = en_name
        self.cn_name = cn_name
        self.user_id = user_id

    def __str__(self):
        return f"en_name: {self.en_name}, cn_name: {self.cn_name}, user_id: {self.user_id}"


class ReqMsg(object):
    def __init__(self, xml_tree):
        user = xml_tree.find('From')
        self.from_user = UserInfo(user.find('Alias').text, user.find('Name').text, user.find('UserId').text)
        self.msg_type = xml_tree.find('MsgType').text
        self.chat_type = xml_tree.find('ChatType').text
        self.chat_id = xml_tree.find('ChatId').text
        self.webhook_url = xml_tree.find('WebhookUrl').text
        self.msg_id = xml_tree.find('MsgId').text
        # GetChatInfoUrl

    @staticmethod
    def create_msg(xml_tree):
        msg_type = xml_tree.find('MsgType').text
        if msg_type == 'text':
            return TextReqMsg(xml_tree)
        elif msg_type == 'event':
            return EventReqMsg(xml_tree)
        elif msg_type == 'image':
            return ImageReqMsg(xml_tree)
        elif msg_type == 'attachment':
            return AttachmentReqMsg(xml_tree)
        elif msg_type == 'mixed':
            return MixedMessageReqMsg(xml_tree)
        else:
            return None


class TextReqMsg(ReqMsg):
    def __init__(self, xml_tree):
        super().__init__(xml_tree)
        self.msg_type = 'text'
        self.content = xml_tree.find('Text').find('Content').text


class EventReqMsg(ReqMsg):
    def __init__(self, xml_tree):
        super().__init__(xml_tree)
        self.msg_type = 'event'
        self.event_type = xml_tree.find('Event').find('EventType').text
        # self.event_key = None


class ImageReqMsg(ReqMsg):
    def __init__(self, xml_tree):
        super().__init__(xml_tree)
        self.msg_type = 'image'
        self.image_url = xml_tree.find('Image').find('ImageUrl').text


class AttachmentAction(object):
    def __init__(self, name, value, type_):
        self.name = name
        self.value = value
        self.type = type_


class AttachmentReqMsg(ReqMsg):
    def __init__(self, xml_tree):
        super().__init__(xml_tree)
        self.msg_type = 'attachment'
        self.callback_id = xml_tree.find('Attachment').find('CallbackId').text
        self.actions = []
        e = xml_tree.find('Attachment').find('Actions')
        self.actions.append(AttachmentAction(e.find('Name').text, e.find('Value').text, e.find('Type').text))


class SimpleTextMsg(object):
    def __init__(self, xml_tree):
        self.msg_type = 'text'
        self.content = xml_tree.find('Text').find('Content').text


class SimpleImageMsg(object):
    def __init__(self, xml_tree):
        self.msg_type = 'image'
        self.image_url = xml_tree.find('Image').find('ImageUrl').text


class MixedMessageReqMsg(ReqMsg):
    def __init__(self, xml_tree):
        super().__init__(xml_tree)
        self.msg_type = 'mixed'
        self.msg_items = []
        for e in xml_tree.find('MixedMessage'):
            if e.find('MsgType').text == 'text':
                self.msg_items.append(SimpleTextMsg(e))
            elif e.find('MsgType').text == 'image':
                self.msg_items.append(SimpleImageMsg(e))
            else:
                raise Exception("unknown msg type")
