import os
import sys
from dotenv import load_dotenv

import auth
import lotto645
import win720
import notification
import time


def get_manual_numbers_from_gpt():
    """ChatGPT API를 사용하여 로또 번호 추천 받기"""
    prompt = (
        "로또 6/45 번호 5세트를 추천해줘. "
        "각 세트는 1~45 사이의 숫자 6개로 구성되어야 하며, 숫자는 중복되지 않아야 해. "
        "다음 형식으로 제공해줘: [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], ...]"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}]
    )

    generated_text = response["choices"][0]["message"]["content"]
    try:
        numbers = json.loads(generated_text)
        return numbers[:5]  # 최대 5세트 반환
    except json.JSONDecodeError:
        return []

def buy_lotto645_manual(authCtrl: auth.AuthController, cnt: int):
    """수동 번호 입력으로 로또 구매"""
    lotto = lotto645.Lotto645()

    # ChatGPT로 자동 생성한 번호 사용
    manual_numbers = get_manual_numbers_from_gpt()

    if not manual_numbers:
        print("ChatGPT로부터 유효한 로또 번호를 가져오지 못했습니다.")
        return {}

    response = lotto.buy_lotto645(authCtrl, cnt, lotto645.Lotto645Mode.MANUAL, manual_numbers)
    response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
    return response


def buy_lotto645(authCtrl: auth.AuthController, cnt: int, mode: str):
    lotto = lotto645.Lotto645()
    _mode = lotto645.Lotto645Mode[mode.upper()]
    response = lotto.buy_lotto645(authCtrl, cnt, _mode)
    response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
    return response

def check_winning_lotto645(authCtrl: auth.AuthController) -> dict:
    lotto = lotto645.Lotto645()
    item = lotto.check_winning(authCtrl)
    return item

def buy_win720(authCtrl: auth.AuthController, username: str):
    pension = win720.Win720()
    response = pension.buy_Win720(authCtrl, username)
    response['balance'] = pension.get_balance(auth_ctrl=authCtrl)
    return response

def check_winning_win720(authCtrl: auth.AuthController) -> dict:
    pension = win720.Win720()
    item = pension.check_winning(authCtrl)
    return item

def send_message(mode: int, lottery_type: int, response: dict, webhook_url: str):
    notify = notification.Notification()

    if mode == 0:
        if lottery_type == 0:
            notify.send_lotto_winning_message(response, webhook_url)
        else:
            notify.send_win720_winning_message(response, webhook_url)
    elif mode == 1: 
        if lottery_type == 0:
            notify.send_lotto_buying_message(response, webhook_url)
        else:
            notify.send_win720_buying_message(response, webhook_url)

def check():
    load_dotenv()

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)
    
    response = check_winning_lotto645(globalAuthCtrl)
    send_message(0, 0, response=response, webhook_url=discord_webhook_url)

    time.sleep(10)
    
    response = check_winning_win720(globalAuthCtrl)
    send_message(0, 1, response=response, webhook_url=discord_webhook_url)

def buy(): 
    
    load_dotenv() 

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    count = int(os.environ.get('COUNT'))
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    openApiKey = os.environ.get('OPEN_API_KEY')

    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)


    response = buy_lotto645(globalAuthCtrl, count, "AUTO")
    send_message(1, 0, response=response, webhook_url=discord_webhook_url)

    time.sleep(10)

    response = buy_win720(globalAuthCtrl, username) 
    send_message(1, 1, response=response, webhook_url=discord_webhook_url)

def run():
    if len(sys.argv) < 2:
        print("Usage: python controller.py [buy|check]")
        return

    if sys.argv[1] == "buy":
        buy()
    elif sys.argv[1] == "check":
        check()
  

if __name__ == "__main__":
    run()
