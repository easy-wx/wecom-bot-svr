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


