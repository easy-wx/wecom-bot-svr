import wecom_bot_svr


def main():
    token = "xxxxxxx"
    aes_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    corp_id = ""
    host = "0.0.0.0"
    port = 5001
    server = wecom_bot_svr.Server("wecom_bot", host, port, token=token, aes_key=aes_key, corp_id=corp_id)

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
