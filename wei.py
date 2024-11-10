import requests

last_message = []


def send_wechat_message(message):
    global last_message
    mess=message[:10]

    if mess in last_message:
        return
    if len(last_message)>1:
        last_message.pop(0)

    last_message.append(mess)

    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bb5866a6-6b48-42f1-b480-072bc524b10b'
    payload = {
        'msgtype': 'text',
        'text': {
            'content': message
        }
    }
    response = requests.post(url, json=payload)
    return response.json()
