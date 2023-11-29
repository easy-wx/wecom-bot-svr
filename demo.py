import app


def main():
    # token = "xxxxxxx"
    # aes_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    token = "hJqcu3uJ9Tn2gXPmxx2w9kkCkCE2EPYo"
    aes_key = "6qkdMrq68nTKduznJYO1A37W2oEgpkMUvkttRToqhUt"
    corp_id = ""
    host = "0.0.0.0"
    port = 5001
    server = app.WecomBotServer("wecom_bot", host, port, token=token, aes_key=aes_key, corp_id=corp_id)

    def msg_handler(user_info, msg_type, content, xml_tree):
        print(user_info, msg_type, content)
        return "hello"

    def event_handler(user_info, event_type, xml_tree):
        print(user_info, event_type)
        return "hello"

    server.set_message_handler(msg_handler)
    server.set_event_handler(event_handler)
    server.run()


if __name__ == '__main__':
    main()
