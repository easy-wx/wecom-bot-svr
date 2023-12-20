from .req_msg import ReqMsg
import xml.etree.cElementTree as ET

msg_str_list = ["""<xml>
	<WebhookUrl> <![CDATA[https://qyapi.weixin.qq.com/xxxxxxx]]></WebhookUrl>
	<ChatId><![CDATA[wrkSFfCgAALFgnrSsWU38puiv4yvExuw]]></ChatId>
	<PostId><![CDATA[bpkSFfCgAAWeiHos2p6lJbG3_F2xxxxx]]></PostId>
	<ChatType>single</ChatType>
	<GetChatInfoUrl><![CDATA[https://qyapi.weixin.qq.com/cgi-bin/webhook/get_chat_info?code=m49c5aRCdEP8_QQdZmTNR52yJ5TLGcIMzaLJk3x5KqY]]></GetChatInfoUrl>
	<From>
		<UserId>zhangsan</UserId>
		<Name><![CDATA[张三]]></Name>
		<Alias><![CDATA[jackzhang]]></Alias>
	</From>
	<MsgType>text</MsgType>
	<Text>
		<Content><![CDATA[@RobotA hello robot]]></Content>
	</Text>
	<MsgId>abcdabcdabcd</MsgId>
</xml>""",
                """<xml>
                    <WebhookUrl> <![CDATA[https://qyapi.weixin.qq.com/xxxxxxx]]></WebhookUrl>
                    <ChatId><![CDATA[wrkSFfCgAALFgnrSsWU38puiv4yvExuw]]></ChatId>
                    <ChatType>single</ChatType>
                    <From>
                        <UserId>zhangsan</UserId>
                        <Name><![CDATA[张三]]></Name>
                        <Alias><![CDATA[jackzhang]]></Alias>
                    </From>
                    <MsgType>image</MsgType>
                    <Image>
                        <ImageUrl><![CDATA[https://p.qpic.cn/pic_wework/2085796/353325df3d4200754264e0521fd8f01e32a878aae7e52a/0]]></ImageUrl>
                    </Image>
                    <MsgId>abcdabcdabcd</MsgId>
                </xml>""",

                """<xml>
                    <WebhookUrl> <![CDATA[https://qyapi.weixin.qq.com/xxxxxxx]]></WebhookUrl>
                    <ChatId><![CDATA[wrkSFfCgAALFgnrSsWU38puiv4yvExuw]]></ChatId>
                    <ChatType>single</ChatType>
                    <GetChatInfoUrl><![CDATA[https://qyapi.weixin.qq.com/cgi-bin/webhook/get_chat_info?code=m49c5aRCdEP8_QQdZmTNR52yJ5TLGcIMzaLJk3x5KqY]]></GetChatInfoUrl>
                    <From>
                        <UserId>zhangsan</UserId>
                        <Name><![CDATA[张三]]></Name>
                        <Alias><![CDATA[jackzhang]]></Alias>
                    </From>
                    <MsgType>event</MsgType>
                    <Event>
                        <EventType><![CDATA[add_to_chat]]></EventType>
                    </Event>
                    <AppVersion><![CDATA[2.8.12.1551]]></AppVersion>
                    <MsgId>abcdabcdabcd</MsgId>
                </xml>""",
                """<xml>
                   <WebhookUrl><![CDATA[http://in.qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx]]></WebhookUrl>
                   <ChatId><![CDATA[xxxxx]]></ChatId>
                   <PostId><![CDATA[bpkSFfCgAAWeiHos2p6lJbG3_F2xxxxx]]></PostId>
                   <ChatType>single</ChatType>
                   <From>
                       <UserId><![CDATA[zhangsan]]></UserId>
                       <Name><![CDATA[张三]]></Name>
                       <Alias><![CDATA[zhangsan]]></Alias>
                   </From>
                   <MsgId><![CDATA[xxxxx]]></MsgId>
                   <MsgType><![CDATA[attachment]]></MsgType>
                   <Attachment>
                       <CallbackId><![CDATA[btn_for_show_more]]></CallbackId>
                       <Actions>
                           <Name><![CDATA[btn_more]]></Name>
                           <Value><![CDATA[btn_more]]></Value>
                           <Type><![CDATA[button]]></Type>
                       </Actions>
                   </Attachment>
               </xml>""",
                """<xml>
                   <WebhookUrl><![CDATA[https://qyapi.weixin.qq.com/xxxxxxxx]]></WebhookUrl>
                   <ChatId><![CDATA[wrkSFfCgAAskBzQgmxxxxxxxxxxxx]]></ChatId>
                   <MsgId><![CDATA[CAEQi5HR8wUY/NGagIOAgAMgXQ==]]></MsgId>
                   <ChatType><![CDATA[group]]></ChatType>
                   <From>
                       <UserId><![CDATA[T434200000]]></UserId>
                       <Name><![CDATA[张三]]></Name>
                       <Alias><![CDATA[jackzhang]]></Alias>
                   </From>
                   <MsgType><![CDATA[mixed]]></MsgType>
                   <MixedMessage>
                       <MsgItem>
                           <MsgType><![CDATA[text]]></MsgType>
                           <Text>
                               <Content><![CDATA[@机器人 这是今日的测试情况]]></Content>
                           </Text>
                       </MsgItem>
                       <MsgItem>
                           <MsgType><![CDATA[image]]></MsgType>
                           <Image>
                               <ImageUrl><![CDATA[http://p.qpic.cn/pic_wework/2698515288/54528347764eac2d194c2ce90d83769c62e478f59e706815/0]]></ImageUrl>
                           </Image>
                       </MsgItem>
                   </MixedMessage>
               </xml>"""]

for msg_str in msg_str_list:
    xml_tree = ET.fromstring(msg_str)
    msg = ReqMsg.create_msg(xml_tree)
    print(msg.msg_type)
    print(msg.from_user)
    print(msg.chat_type)
    print(msg.chat_id)
    print(msg.webhook_url)
    print(msg.msg_id)
    if msg.msg_type == 'text':
        print(msg.content)
    elif msg.msg_type == 'event':
        print(msg.event_type)
    elif msg.msg_type == 'image':
        print(msg.image_url)
    elif msg.msg_type == 'attachment':
        print(msg.callback_id)
        for action in msg.actions:
            print(action.name)
            print(action.value)
            print(action.type)
    elif msg.msg_type == 'mixed':
        for msg_item in msg.msg_items:
            print(msg_item.msg_type)
            if msg_item.msg_type == 'text':
                print(msg_item.content)
            elif msg_item.msg_type == 'image':
                print(msg_item.image_url)
    else:
        print("unknown msg type")
    print()
