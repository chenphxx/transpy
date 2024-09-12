import requests
import json
import pyperclip
import re


# 账号信息
endpoint = your_endpoint
huawei_account = your_account
IAM_user = your_user
password = your_password
project = your_project

# 获取IAM Token
def get_iam_token():
    url = f"https://iam.{endpoint}.myhuaweicloud.com/v3/auth/tokens"
    # 请求头
    headers = \
    {
        'Content-Type': 'application/json'
    }
    # 请求体
    payload = \
    {
        "auth":
        {
            "identity":
            {
                "methods" : ["password"],
                "password":
                {
                    "user":
                    {
                        "domain":
                        {
                        "name": huawei_account
                        },
                    "name": IAM_user,
                    "password": password
                    }
                }
            },
            "scope":
            {
                "project":
                {
                    "name": endpoint
                }
            }
        }
    }

    # 发送POST请求
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    # 检查响应状态
    if response.status_code == 201:
        token = response.headers.get('X-Subject-Token')  # 获取Token
        # print("获取的Token:", token)
        return token
    else:
        print("获取Token失败:", response.status_code, response.text)
        return None

# 判断文本语言
def zh_en():
    text = str(pyperclip.paste())
    japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]+')  # 日语匹配
    for ch in text:
        if bool(japanese_pattern.search(text)):
            return "auto"
        elif '\u4e00' <= ch <= '\u9fff':  # 简体中文
            return "zh"
        else:
            return "auto"

# 使用API翻译
def nlp_demo(token):
    # 判断目标语言和源语言; 如果源语言为中文, 则翻译为英文, 如果为其他语言则全部翻译为中文
    src_language = zh_en()
    if src_language == "zh":
        aim_language = "en"
    else:
        aim_language = "zh"

    url = f"https://nlp-ext.{endpoint}.myhuaweicloud.com/v1/{project}/machine-translation/text-translation"
    header = \
    {
        'Content-Type': 'application/json',
        'X-Auth-Token': token
    }
    body = \
    {
        'text': str(pyperclip.paste()),  # 从剪贴板读取文本
        'from': str(src_language),  # 文本语言
        'to': str(aim_language),  # 目标语言
        'scene': 'common'
    }
    response = requests.post(url, data=json.dumps(body), headers=header)
    # print(response.json())
    return response


if __name__ == "__main__":
    token = get_iam_token()
    print(token)
