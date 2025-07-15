import requests
import re

class Notification:
    def send_lotto_buying_message(self, body: dict, webhook_url: str) -> None:
        assert type(webhook_url) == str

        # 빈 응답 체크
        if not body:
            message = "⚠️ 로또 구매 실패: 응답 데이터가 없습니다."
            self._send_discord_webhook(webhook_url, message)
            return

        result = body.get("result", {})
        result_msg = result.get("resultMsg", "FAILURE")
        purchase_method = body.get("purchase_method", "UNKNOWN")
        
        # 구매 성공 시
        if result_msg.upper() == "SUCCESS":
            lotto_number_str = self.make_lotto_number_message(result["arrGameChoiceNum"])
            
            # 구매 방법에 따른 메시지 구성
            if purchase_method == "CHATGPT_MANUAL":
                method_emoji = "🤖"
                method_text = "ChatGPT 추천 번호로 수동 구매"
            elif purchase_method == "AUTO_FALLBACK":
                method_emoji = "🔄"
                method_text = "ChatGPT 실패 → 자동 번호 구매"
            elif purchase_method == "AUTO_FALLBACK_AFTER_MANUAL_FAIL":
                method_emoji = "🔄"
                method_text = "수동 구매 실패 → 자동 번호 구매"
            else:
                method_emoji = "✅"
                method_text = "로또 구매"
            
            message = f"{method_emoji} {result['buyRound']}회 {method_text} 완료 💰 남은잔액: {body['balance']}\n```{lotto_number_str}```"
            self._send_discord_webhook(webhook_url, message)
        else:
            # 구매 실패 시
            balance = body.get('balance', '확인불가')
            error_msg = result.get("resultMsg", "알 수 없는 오류")
            
            # 실패 유형에 따른 메시지 구성
            if "ChatGPT" in error_msg:
                failure_type = "🤖 ChatGPT 오류"
            elif "자동 구매" in error_msg:
                failure_type = "🔄 자동 구매 실패"
            else:
                failure_type = "❌ 구매 실패"
                
            message = f"{failure_type}\n• 오류: {error_msg}\n• 잔액: {balance}"
            self._send_discord_webhook(webhook_url, message)

    def make_lotto_number_message(self, lotto_number: list) -> str:
        assert type(lotto_number) == list

        # parse list without last number 3
        lotto_number = [x[:-1] for x in lotto_number]
        
        # remove alphabet and | replace white space  from lotto_number
        lotto_number = [x.replace("|", " ") for x in lotto_number]
        
        # lotto_number to string 
        lotto_number = '\n'.join(x for x in lotto_number)
        
        return lotto_number

    def send_win720_buying_message(self, body: dict, webhook_url: str) -> None:
        
        if body.get("resultCode") != '100':  
            return       

        win720_round = body.get("resultMsg").split("|")[3]

        win720_number_str = self.make_win720_number_message(body.get("saleTicket"))
        message = f"{win720_round}회 연금복권 구매 완료 :moneybag: 남은잔액 : {body['balance']}\n```\n{win720_number_str}```"
        self._send_discord_webhook(webhook_url, message)

    def make_win720_number_message(self, win720_number: str) -> str:
        formatted_numbers = []
        for number in win720_number.split(","):
            formatted_number = f"{number[0]}조 " + " ".join(number[1:])
            formatted_numbers.append(formatted_number)
        return "\n".join(formatted_numbers)

    def send_lotto_winning_message(self, winning: dict, webhook_url: str) -> None: 
        assert type(winning) == dict
        assert type(webhook_url) == str

        try: 
            round = winning["round"]
            money = winning["money"]

            max_label_status_length = max(len(f"{line['label']} {line['status']}") for line in winning["lotto_details"])

            formatted_lines = []
            for line in winning["lotto_details"]:
                line_label_status = f"{line['label']} {line['status']}".ljust(max_label_status_length)
                line_result = line["result"]

                formatted_nums = []
                for num in line_result:
                    raw_num = re.search(r'\d+', num).group()
                    formatted_num = f"{int(raw_num):02d}"
                    if '✨' in num:
                        formatted_nums.append(f"[{formatted_num}]")
                    else:
                        formatted_nums.append(f" {formatted_num} ")

                formatted_nums = [f"{num:>6}" for num in formatted_nums]

                formatted_line = f"{line_label_status} " + " ".join(formatted_nums)
                formatted_lines.append(formatted_line)

            formatted_results = "\n".join(formatted_lines)

            if winning['money'] != "-":
                winning_message = f"로또 *{winning['round']}회* - *{winning['money']}* 당첨 되었습니다 🎉"
            else:
                winning_message = f"로또 *{winning['round']}회* - 다음 기회에... 🫠"

            self._send_discord_webhook(webhook_url, f"```ini\n{formatted_results}```\n{winning_message}")
        except KeyError:
            return

    def send_win720_winning_message(self, winning: dict, webhook_url: str) -> None: 
        assert type(winning) == dict
        assert type(webhook_url) == str

        try: 
            round = winning["round"]
            money = winning["money"]

            if winning['money'] != "-":
                message = f"연금복권 *{winning['round']}회* - *{winning['money']}* 당첨 되었습니다 🎉"

            self._send_discord_webhook(webhook_url, message)
        except KeyError:
            message = f"연금복권 - 다음 기회에... 🫠"
            self._send_discord_webhook(webhook_url, message)
            return

    def _send_discord_webhook(self, webhook_url: str, message: str) -> None:        
        payload = { "text": message }
        headers = { "Content-Type": "application/json" }
        requests.post(webhook_url, json=payload, headers=headers)
