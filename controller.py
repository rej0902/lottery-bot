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
    
    def get_chatgpt_recommendation(prompt_text, attempt_type="main"):
        """ChatGPT API 호출 및 파싱"""
        try:
            client = OpenAI(api_key=os.environ.get('OPEN_API_KEY'))
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional lottery number recommendation expert. You must only respond with valid lottery numbers between 1-45. Do not include any symbols like '*' or invalid characters. Always return exactly 5 sets of 6 numbers each in the specified format."},
                    {"role": "user", "content": prompt_text}
                ]
            )

            generated_text = response.choices[0].message.content
            print(f"ChatGPT 응답 ({attempt_type}): {generated_text}")
            
            # 파싱 로직 (기존과 동일)
            numbers = []
            
            # 1. 표준 JSON 형식 시도
            match = re.search(r'\[\s*\[.*?\]\s*\]', generated_text, re.DOTALL)
            if match:
                try:
                    list_str = match.group()
                    parsed_numbers = json.loads(list_str)
                    for num_set in parsed_numbers:
                        if validate_number_set(num_set):
                            numbers.append(num_set)
                    if numbers:
                        print(f"JSON 형식으로 파싱 성공: {numbers}")
                        return numbers
                except json.JSONDecodeError:
                    print("JSON 파싱 실패")
            
            # 2. 대괄호 형식 찾기
            if not numbers:
                bracket_matches = re.findall(r'\[([^\]]+)\]', generated_text)
                for match in bracket_matches:
                    try:
                        elements = match.split(',')
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
            
            # 3. 일반 텍스트에서 번호 추출
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
            
            # 4. 콤마로 구분된 숫자 찾기
            if not numbers:
                pattern = r'(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)'
                matches = re.findall(pattern, generated_text)
                for match in matches:
                    try:
                        valid_nums = []
                        for num_str in match:
                            if is_valid_lotto_number(num_str):
                                valid_nums.append(int(num_str))
                        
                        if len(valid_nums) == 6 and validate_number_set(valid_nums):
                            numbers.append(valid_nums)
                    except (ValueError, AttributeError):
                        continue
            
            return numbers
            
        except Exception as e:
            print(f"ChatGPT API 호출 중 오류 발생 ({attempt_type}): {e}")
            return []
    
    # 로또 통계 데이터 가져오기
    lotto = lotto645.Lotto645()
    
    # 먼저 통계 데이터 수집 시도
    try:
        stats = lotto.fetch_lotto_statistics()
        no_show_numbers = lotto.fetch_recent_no_show_numbers()
        recent_winners = lotto.fetch_recent_winning_numbers(5)
        
        # 통계 데이터가 충분히 수집되었는지 확인
        stats_available = bool(stats and len(stats) > 30)  # 최소 30개 번호 통계
        no_show_available = bool(no_show_numbers and len(no_show_numbers) > 5)  # 최소 5개 미출현 번호
        recent_available = bool(recent_winners and len(recent_winners) > 3)  # 최소 3개 회차
        
        if stats_available and no_show_available and recent_available:
            print("📊 통계 데이터 수집 성공 - 상세 분석 프롬프트 사용")
            
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
            
            # 미출현 번호 정리
            no_show_text = "⏰ 최근 미출현 번호들:\n"
            if no_show_numbers:
                no_show_text += f"{', '.join(no_show_numbers)}\n"
            
            # 최근 당첨 번호 정리
            recent_text = "🎯 최근 당첨 번호 패턴:\n"
            if recent_winners:
                for winner in recent_winners:
                    recent_text += f"{winner['round']}회 ({winner['date']}): {winner['numbers']} (보너스: {winner['bonus']})\n"
            
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
            
            # 상세 분석 프롬프트로 시도
            numbers = get_chatgpt_recommendation(prompt, "상세분석")
            
            if numbers and len(numbers) >= 5:
                print(f"✅ 상세 분석 기반 추천 성공: {numbers[:5]}")
                return numbers[:5]
        
        print("⚠️ 통계 데이터 불충분 또는 수집 실패 - 역대 당첨 번호 기반 프롬프트 사용")
        
    except Exception as e:
        print(f"⚠️ 통계 데이터 수집 실패: {e} - 역대 당첨 번호 기반 프롬프트 사용")
    
    # Fallback: 역대 당첨 번호 기반 프롬프트
    try:
        recent_winners = lotto.fetch_recent_winning_numbers(10)  # 더 많은 회차 수집
        
        if recent_winners:
            recent_text = "🎯 역대 당첨 번호 패턴 (최근 10회차):\n"
            for winner in recent_winners:
                recent_text += f"{winner['round']}회: {winner['numbers']}\n"
        else:
            recent_text = "역대 당첨 번호 데이터를 사용할 수 없습니다."
        
        fallback_prompt = f"""당신은 로또 번호 추천 전문가입니다. 다음 역대 당첨 번호 패턴을 분석하여 로또 6/45 번호 5세트를 추천해주세요.

{recent_text}

분석 요청사항:
1. 역대 당첨 번호에서 자주 나타나는 번호들을 파악
2. 번호 분포 패턴을 고려하여 1-45 범위에서 고르게 선택
3. 연속된 번호의 출현 빈도를 고려
4. 홀수와 짝수의 균형을 맞춤
5. 각 세트는 1~45 사이의 숫자 6개로 구성되어야 하며, 숫자는 중복되지 않아야 합니다.

중요: 반드시 유효한 1-45 범위의 정수만 사용하세요. 다음 형식으로만 답변해주세요:
[[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18], [19, 20, 21, 22, 23, 24], [25, 26, 27, 28, 29, 30]]"""
        
        numbers = get_chatgpt_recommendation(fallback_prompt, "역대당첨번호기반")
        
        if numbers and len(numbers) >= 5:
            print(f"✅ 역대 당첨 번호 기반 추천 성공: {numbers[:5]}")
            return numbers[:5]
        elif numbers and len(numbers) > 0:
            print(f"⚠️ 일부 유효한 번호 발견: {numbers}")
            additional_sets = generate_fallback_numbers(5 - len(numbers))
            numbers.extend(additional_sets)
            print(f"📝 기본값으로 채워진 최종 번호: {numbers}")
            return numbers
        
    except Exception as e:
        print(f"⚠️ 역대 당첨 번호 기반 추천도 실패: {e}")
    
    # 최종 Fallback: 기본 번호 생성
    print("🔄 모든 ChatGPT 시도 실패 - 기본 번호 생성")
    return generate_fallback_numbers()

def buy_lotto645_manual(authCtrl: auth.AuthController, cnt: int):
    """수동 번호 입력으로 로또 구매 (실패 시 자동 구매로 fallback)"""
    lotto = lotto645.Lotto645()

    # ChatGPT로 자동 생성한 번호 사용
    manual_numbers = get_manual_numbers_from_gpt()

    if not manual_numbers:
        print("⚠️ ChatGPT로부터 유효한 로또 번호를 가져오지 못했습니다.")
        print("🔄 자동 번호 구매로 전환합니다.")
        
        # 자동 번호 구매로 fallback
        try:
            response = lotto.buy_lotto645(authCtrl, cnt, lotto645.Lotto645Mode.AUTO)
            response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
            
            # 자동 구매 성공 시 메시지에 표시할 정보 추가
            if response.get('result', {}).get('resultMsg', '').upper() == 'SUCCESS':
                response['purchase_method'] = 'AUTO_FALLBACK'
                print("✅ 자동 번호 구매 성공")
            
            return response
            
        except Exception as e:
            print(f"❌ 자동 번호 구매도 실패: {e}")
            return {
                "result": {
                    "resultMsg": f"ChatGPT 실패 후 자동 구매도 실패: {str(e)}",
                    "buyRound": "알 수 없음"
                },
                "balance": "확인불가",
                "purchase_method": "FAILED"
            }

    # ChatGPT 번호로 수동 구매 시도
    try:
        print(f"🤖 ChatGPT 추천 번호로 수동 구매 시도: {len(manual_numbers)}개 세트")
        response = lotto.buy_lotto645(authCtrl, cnt, lotto645.Lotto645Mode.MANUAL, manual_numbers)
        response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
        
        # 수동 구매 성공 시 메시지에 표시할 정보 추가
        if response.get('result', {}).get('resultMsg', '').upper() == 'SUCCESS':
            response['purchase_method'] = 'CHATGPT_MANUAL'
            print("✅ ChatGPT 추천 번호로 수동 구매 성공")
        
        return response
        
    except Exception as e:
        print(f"⚠️ ChatGPT 추천 번호로 수동 구매 실패: {e}")
        print("🔄 자동 번호 구매로 전환합니다.")
        
        # 수동 구매 실패 시 자동 구매로 fallback
        try:
            response = lotto.buy_lotto645(authCtrl, cnt, lotto645.Lotto645Mode.AUTO)
            response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
            
            # 자동 구매 성공 시 메시지에 표시할 정보 추가
            if response.get('result', {}).get('resultMsg', '').upper() == 'SUCCESS':
                response['purchase_method'] = 'AUTO_FALLBACK_AFTER_MANUAL_FAIL'
                print("✅ 자동 번호 구매 성공")
            
            return response
            
        except Exception as e2:
            print(f"❌ 자동 번호 구매도 실패: {e2}")
            return {
                "result": {
                    "resultMsg": f"수동 구매 실패({str(e)}) 후 자동 구매도 실패: {str(e2)}",
                    "buyRound": "알 수 없음"
                },
                "balance": "확인불가",
                "purchase_method": "FAILED"
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
