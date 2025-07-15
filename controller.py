import os
import sys
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

import auth
import lotto645
import win720
import notification
import time


def get_manual_numbers_from_gpt():
    """ChatGPT API를 사용하여 로또 번호 추천 받기"""
    
    def is_valid_lotto_number(num_str):
        """유효한 로또 번호인지 엄격하게 검증"""
        try:
            # 숫자만 포함하는지 확인
            if not re.match(r'^\d+$', num_str.strip()):
                return False
            num = int(num_str.strip())
            return 1 <= num <= 45
        except (ValueError, AttributeError):
            return False
    
    def validate_number_set(nums):
        """번호 세트가 유효한지 검증"""
        if not isinstance(nums, list) or len(nums) != 6:
            return False
        
        # 모든 번호가 1-45 범위이고 중복이 없는지 확인
        if not all(isinstance(num, int) and 1 <= num <= 45 for num in nums):
            return False
        
        # 중복 확인
        if len(set(nums)) != 6:
            return False
            
        return True
    
    def generate_fallback_numbers(count=5):
        """ChatGPT 실패 시 기본 번호 생성"""
        import random
        fallback_numbers = []
        for _ in range(count):
            nums = sorted(random.sample(range(1, 46), 6))
            fallback_numbers.append(nums)
        return fallback_numbers
    
    # 로또 통계 데이터 가져오기
    lotto = lotto645.Lotto645()
    stats = lotto.fetch_lotto_statistics()
    no_show_numbers = lotto.fetch_recent_no_show_numbers()
    recent_winners = lotto.fetch_recent_winning_numbers(5)
    
    # 통계 데이터 정리
    stats_text = ""
    if stats:
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['frequency'], reverse=True)
        stats_text = "📊 로또 당첨 번호 통계 (빈도 높은 순):\n"
        for number, data in sorted_stats[:10]:  # 상위 10개만 표시
            stats_text += f"번호 {number}: {data['frequency']}회 당첨 ({data['percentage']})\n"
        
        stats_text += "\n📉 빈도가 낮은 번호들:\n"
        for number, data in sorted_stats[-10:]:  # 하위 10개
            stats_text += f"번호 {number}: {data['frequency']}회 당첨 ({data['percentage']})\n"
    else:
        stats_text = "통계 데이터를 가져올 수 없습니다."
    
    # 미출현 번호 정리
    no_show_text = "⏰ 최근 미출현 번호들:\n"
    if no_show_numbers:
        no_show_text += f"{', '.join(no_show_numbers)}\n"
    else:
        no_show_text += "미출현 번호 데이터를 가져올 수 없습니다.\n"
    
    # 최근 당첨 번호 정리
    recent_text = "🎯 최근 당첨 번호 패턴:\n"
    if recent_winners:
        for winner in recent_winners:
            recent_text += f"{winner['round']}회 ({winner['date']}): {winner['numbers']} (보너스: {winner['bonus']})\n"
    else:
        recent_text += "최근 당첨 번호 데이터를 가져올 수 없습니다.\n"
    
    prompt = f"""당신은 로또 번호 추천 전문가입니다. 다음 종합 통계 데이터를 기반으로 로또 6/45 번호 5세트를 추천해주세요.

{stats_text}

{no_show_text}

{recent_text}

통계적 분석 요청사항:
1. 과거 당첨 빈도가 높은 번호와 낮은 번호를 적절히 조합
2. 최근 미출현 번호를 우선적으로 고려 (출현 확률이 높아질 수 있음)
3. 최근 당첨 번호 패턴을 분석하여 피해야 할 번호와 선택해야 할 번호 구분
4. 번호 분포를 고려하여 1-45 범위에서 고르게 선택
5. 연속된 번호 조합과 홀짝 균형을 고려
6. 각 세트는 1~45 사이의 숫자 6개로 구성되어야 하며, 숫자는 중복되지 않아야 합니다.

중요: 반드시 유효한 1-45 범위의 정수만 사용하세요. 다음 형식으로만 답변해주세요:
[[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18], [19, 20, 21, 22, 23, 24], [25, 26, 27, 28, 29, 30]]"""

    try:
        client = OpenAI(api_key=os.environ.get('OPEN_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional lottery number recommendation expert. You must only respond with valid lottery numbers between 1-45. Do not include any symbols like '*' or invalid characters. Always return exactly 5 sets of 6 numbers each in the specified format."},
                {"role": "user", "content": prompt}
            ]
        )

        generated_text = response.choices[0].message.content
        print(f"ChatGPT 응답: {generated_text}")
        
        # 다양한 형식으로 번호 추출 시도
        numbers = []
        
        # 1. 표준 JSON 형식 시도
        match = re.search(r'\[\s*\[.*?\]\s*\]', generated_text, re.DOTALL)
        if match:
            try:
                list_str = match.group()
                parsed_numbers = json.loads(list_str)
                # 각 세트를 엄격하게 검증
                for num_set in parsed_numbers:
                    if validate_number_set(num_set):
                        numbers.append(num_set)
                if numbers:
                    print(f"JSON 형식으로 파싱 성공: {numbers}")
            except json.JSONDecodeError:
                print("JSON 파싱 실패")
        
        # 2. 대괄호 형식 찾기 [1, 2, 3, 4, 5, 6]
        if not numbers:
            bracket_matches = re.findall(r'\[([^\]]+)\]', generated_text)
            for match in bracket_matches:
                try:
                    # 콤마로 분리된 요소들 검증
                    elements = match.split(',')
                    if len(elements) == 6:
                        # 각 요소가 유효한 숫자인지 엄격하게 검증
                        valid_nums = []
                        for elem in elements:
                            elem = elem.strip()
                            if is_valid_lotto_number(elem):
                                valid_nums.append(int(elem))
                        
                        if len(valid_nums) == 6 and validate_number_set(valid_nums):
                            numbers.append(valid_nums)
                except (ValueError, AttributeError):
                    continue
        
        # 3. 일반 텍스트에서 번호 추출 (1. [7, 13, 25, 28, 32, 42] 형식)
        if not numbers:
            lines = generated_text.split('\n')
            for line in lines:
                if '[' in line and ']' in line:
                    try:
                        bracket_content = re.search(r'\[([^\]]+)\]', line)
                        if bracket_content:
                            content = bracket_content.group(1)
                            elements = content.split(',')
                            if len(elements) == 6:
                                valid_nums = []
                                for elem in elements:
                                    elem = elem.strip()
                                    if is_valid_lotto_number(elem):
                                        valid_nums.append(int(elem))
                                
                                if len(valid_nums) == 6 and validate_number_set(valid_nums):
                                    numbers.append(valid_nums)
                    except (ValueError, AttributeError):
                        continue
        
        # 4. 콤마로 구분된 숫자 찾기 (7, 13, 25, 28, 32, 42 형식)
        if not numbers:
            # 6개의 연속된 유효한 숫자 패턴 찾기
            pattern = r'(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)'
            matches = re.findall(pattern, generated_text)
            for match in matches:
                try:
                    # 각 매치된 요소가 유효한 로또 번호인지 확인
                    valid_nums = []
                    for num_str in match:
                        if is_valid_lotto_number(num_str):
                            valid_nums.append(int(num_str))
                    
                    if len(valid_nums) == 6 and validate_number_set(valid_nums):
                        numbers.append(valid_nums)
                except (ValueError, AttributeError):
                    continue
        
        # 최종 검증 및 중복 제거
        if numbers:
            unique_numbers = []
            for num_set in numbers:
                if validate_number_set(num_set) and num_set not in unique_numbers:
                    unique_numbers.append(num_set)
            
            if len(unique_numbers) >= 5:
                print(f"추천받은 로또 번호: {unique_numbers[:5]}")
                return unique_numbers[:5]
            elif len(unique_numbers) > 0:
                print(f"일부 유효한 번호 발견: {unique_numbers}")
                # 부족한 세트는 기본값으로 채움
                additional_sets = generate_fallback_numbers(5 - len(unique_numbers))
                unique_numbers.extend(additional_sets)
                print(f"기본값으로 채워진 최종 번호: {unique_numbers}")
                return unique_numbers
        
        # 모든 파싱 실패 시 기본값 반환
        print("ChatGPT 응답에서 유효한 번호를 찾을 수 없습니다. 기본값을 반환합니다.")
        return generate_fallback_numbers()
            
    except Exception as e:
        print(f"ChatGPT API 호출 중 오류 발생: {e}")
        print("기본값을 반환합니다.")
        return generate_fallback_numbers()

def buy_lotto645_manual(authCtrl: auth.AuthController, cnt: int):
    """수동 번호 입력으로 로또 구매"""
    lotto = lotto645.Lotto645()

    # ChatGPT로 자동 생성한 번호 사용
    manual_numbers = get_manual_numbers_from_gpt()

    if not manual_numbers:
        print("ChatGPT로부터 유효한 로또 번호를 가져오지 못했습니다.")
        # 에러 응답 반환
        return {
            "result": {
                "resultMsg": "ChatGPT 번호 생성 실패",
                "buyRound": "알 수 없음"
            },
            "balance": "확인불가"
        }

    try:
        response = lotto.buy_lotto645(authCtrl, cnt, lotto645.Lotto645Mode.MANUAL, manual_numbers)
        response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
        return response
    except Exception as e:
        print(f"로또 구매 중 오류 발생: {e}")
        return {
            "result": {
                "resultMsg": f"로또 구매 오류: {str(e)}",
                "buyRound": "알 수 없음"
            },
            "balance": "확인불가"
        }


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

    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)
    
    response = check_winning_lotto645(globalAuthCtrl)
    send_message(0, 0, response=response, webhook_url=slack_webhook_url)

    time.sleep(10)
    
    response = check_winning_win720(globalAuthCtrl)
    send_message(0, 1, response=response, webhook_url=slack_webhook_url)

def buy(): 
    
    load_dotenv() 

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    count = int(os.environ.get('COUNT'))
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    openai_api_key = os.environ.get('OPEN_API_KEY')

    # OpenAI API 키 설정 - 새로운 방식에서는 환경변수로 설정
    if openai_api_key:
        os.environ['OPEN_API_KEY'] = openai_api_key

    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)

    # ChatGPT API를 이용한 수동 번호 구매로 변경
    response = buy_lotto645_manual(globalAuthCtrl, count)
    send_message(1, 0, response=response, webhook_url=slack_webhook_url)

    time.sleep(10)

    response = buy_win720(globalAuthCtrl, username) 
    send_message(1, 1, response=response, webhook_url=slack_webhook_url)

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
