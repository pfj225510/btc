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

    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35a935b3-db6c-436c-9965-a2261fc3dabf'
    payload = {
        'msgtype': 'text',
        'text': {
            'content': message
        }
    }
    response = requests.post(url, json=payload)
    return response.json()
