import json
import datetime
import base64
import requests
import re

from enum import Enum
from bs4 import BeautifulSoup as BS
from datetime import timedelta
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

from HttpClient import HttpClientSingleton

import auth


def safe_json_parse(text, fallback=None):
    """
    안전한 JSON 파싱 함수
    - 빈 문자열, None, 잘못된 형식 등을 처리
    - 파싱 실패 시 fallback 값 반환
    """
    if not text or not isinstance(text, str):
        return fallback
    
    text = text.strip()
    if not text:
        return fallback
    
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"JSON 파싱 실패: {e}")
        print(f"문제 텍스트: {repr(text)}")
        return fallback

class Win720:

    keySize = 128
    iterationCount = 1000
    BlockSize = 16
    keyCode = ""

    _pad = lambda self, s: s + (self.BlockSize - len(s) % self.BlockSize) * chr(self.BlockSize - len(s) % self.BlockSize)
    _unpad = lambda self, s : s[:-ord(s[len(s)-1:])]

    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Connection": "keep-alive",
        "sec-ch-ua": '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        "sec-ch-ua-mobile": "?0",
        "Origin": "https://el.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://el.dhlottery.co.kr/game/pension720/game.jsp",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "sec-ch-ua-platform": "\"Windows\"",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,ko-KR;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest"
    }

    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def buy_Win720(
        self, 
        auth_ctrl: auth.AuthController,
        username: str
    ) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        headers = self._generate_req_headers(auth_ctrl)

        self.keyCode = headers['Cookie'].split("JSESSIONID=")[1]
        win720_round = self._get_round()
        
        makeAutoNum_ret = self._makeAutoNumbers(auth_ctrl, win720_round)
        
        # 안전한 JSON 파싱
        auto_num_data = safe_json_parse(makeAutoNum_ret, {})
        if not auto_num_data or 'q' not in auto_num_data:
            print(f"❌ makeAutoNumbers 응답 파싱 실패: {makeAutoNum_ret}")
            return {"error": "makeAutoNumbers 파싱 실패"}
        
        parsed_ret = self._decText(auto_num_data['q'])
        extracted_data = safe_json_parse(parsed_ret, {})
        if not extracted_data or 'selLotNo' not in extracted_data:
            print(f"❌ selLotNo 파싱 실패: {parsed_ret}")
            return {"error": "selLotNo 파싱 실패"}
        
        extracted_num = extracted_data["selLotNo"]
        orderNo, orderDate = self._doOrderRequest(auth_ctrl, win720_round, extracted_num)
        
        conn_pro_result = self._doConnPro(auth_ctrl, win720_round, extracted_num, username, orderNo, orderDate)
        body = safe_json_parse(conn_pro_result, {})
        if not body:
            print(f"❌ connPro 응답 파싱 실패: {conn_pro_result}")
            return {"error": "connPro 파싱 실패"}

        self._show_result(body)
        return body

    def _generate_req_headers(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController
        return auth_ctrl.add_auth_cred_to_headers(self._REQ_HEADERS)

    def _get_round(self) -> str:
        res = self.http_client.get("https://www.dhlottery.co.kr/common.do?method=main")
        html = res.text
        soup = BS(
            html, "html5lib"
        )  # 'html5lib' : in case that the html don't have clean tag pairs
        last_drawn_round = int(soup.find("strong", id="drwNo720").text)
        return str(last_drawn_round + 1)

    def _makeAutoNumbers(self, auth_ctrl: auth.AuthController, win720_round: str) -> str:
        payload = "ROUND={}&SEL_NO=&BUY_CNT=&AUTO_SEL_SET=SA&SEL_CLASS=&BUY_TYPE=A&ACCS_TYPE=01".format(win720_round)
        headers = self._generate_req_headers(auth_ctrl)
        
        data = {
            "q": requests.utils.quote(self._encText(payload))
        }

        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/game/pension720/process/makeAutoNo.jsp", 
            headers=headers,
            data=data
        )

        return res.text

    def _doOrderRequest(self, auth_ctrl: auth.AuthController, win720_round: str, extracted_num: str) -> str:
        payload = "ROUND={}&AUTO_SEL_SET=SA&SEL_CLASS=&SEL_NO={}&BUY_TYPE=M&BUY_CNT=5".format(win720_round, extracted_num)
        headers = self._generate_req_headers(auth_ctrl)

        data = {
            "q": requests.utils.quote(self._encText(payload))
        }

        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/game/pension720/process/makeOrderNo.jsp", 
            headers=headers,
            data=data
        )

        response_data = safe_json_parse(res.text, {})
        if not response_data or 'q' not in response_data:
            print(f"❌ doOrderRequest 응답 파싱 실패: {res.text}")
            return None, None
        
        decrypted_text = self._decText(response_data['q'])
        ret = safe_json_parse(decrypted_text, {})
        if not ret:
            print(f"❌ doOrderRequest 복호화 파싱 실패: {decrypted_text}")
            return None, None

        return ret['orderNo'], ret['orderDate']

    def _doConnPro(self, auth_ctrl: auth.AuthController, win720_round: str, extracted_num: str, username: str, orderNo: str, orderDate: str) -> str:
        payload = "ROUND={}&FLAG=&BUY_KIND=01&BUY_NO={}&BUY_CNT=5&BUY_SET_TYPE=SA%2CSA%2CSA%2CSA%2CSA&BUY_TYPE=A%2CA%2CA%2CA%2CA%2C&CS_TYPE=01&orderNo={}&orderDate={}&TRANSACTION_ID=&WIN_DATE=&USER_ID={}&PAY_TYPE=&resultErrorCode=&resultErrorMsg=&resultOrderNo=&WORKING_FLAG=true&NUM_CHANGE_TYPE=&auto_process=N&set_type=SA&classnum=&selnum=&buytype=M&num1=&num2=&num3=&num4=&num5=&num6=&DSEC=34&CLOSE_DATE=&verifyYN=N&curdeposit=&curpay=5000&DROUND={}&DSEC=0&CLOSE_DATE=&verifyYN=N&lotto720_radio_group=on".format(win720_round,"".join([ "{}{}%2C".format(i,extracted_num) for i in range(1,6)])[:-3],orderNo, orderDate, username, win720_round)
        headers = self._generate_req_headers(auth_ctrl)
        
        data = {
            "q": requests.utils.quote(self._encText(payload))
        }
        
        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/game/pension720/process/connPro.jsp", 
            headers=headers,
            data=data
        )

        response_data = safe_json_parse(res.text, {})
        if not response_data or 'q' not in response_data:
            print(f"❌ doConnPro 응답 파싱 실패: {res.text}")
            return "{}"
        
        ret = self._decText(response_data['q'])
        
        return ret

    def _encText(self, plainText: str) -> str:
        encSalt = get_random_bytes(32)
        encIV = get_random_bytes(16)
        passPhrase = self.keyCode[:32]
        encKey = PBKDF2(passPhrase, encSalt, self.BlockSize, count=self.iterationCount, hmac_hash_module=SHA256)
        aes = AES.new(encKey, AES.MODE_CBC, encIV)

        plainText = self._pad(plainText).encode('utf-8')

        return "{}{}{}".format(bytes.hex(encSalt), bytes.hex(encIV), base64.b64encode(aes.encrypt(plainText)).decode('utf-8'))

    def _decText(self, encText: str) -> str:

        decSalt = bytes.fromhex(encText[0:64])
        decIv = bytes.fromhex(encText[64:96])
        cryptText = encText[96:]
        passPhrase = self.keyCode[:32]
        decKey = PBKDF2(passPhrase, decSalt, self.BlockSize, count=self.iterationCount, hmac_hash_module=SHA256)

        aes = AES.new(decKey, AES.MODE_CBC, decIv)

        return self._unpad(aes.decrypt(base64.b64decode(cryptText)).decode('utf-8'))

    def get_balance(self, auth_ctrl: auth.AuthController) -> str: 
        
        headers = self._generate_req_headers(auth_ctrl)
        res = self.http_client.post(
            url="https://dhlottery.co.kr/userSsl.do?method=myPage", 
            headers=headers
        )

        html = res.text
        soup = BS(
            html, "html5lib"
        )
        balance = soup.find("p", class_="total_new").find('strong').text
        return balance

    def check_winning(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        headers = self._generate_req_headers(auth_ctrl)

        parameters = self._make_search_date()
        data = {
            "nowPage": 1, 
            "searchStartDate": parameters["searchStartDate"],
            "searchEndDate": parameters["searchEndDate"],
            "winGrade": 1,
            "lottoId": "LP72", 
            "sortOrder": "DESC"
        }

        res = self.http_client.post(
            "https://dhlottery.co.kr/myPage.do?method=lottoBuyList",
            headers=headers,
            data=data
        )

        html = res.text
        soup = BS(html, "html5lib")
        
        winnings = soup.find("table", class_="tbl_data tbl_data_col").find_all("tbody")[0].find_all("td")       

        result_data = {
            "data": "no winning data"
        }

        if len(winnings) == 1:
            return result_data

        result_data = {
            "round": winnings[2].text.strip(),
            "money": ",".join([ winnings[6+(i*8)].text.strip() for i in range(0,int(len(winnings)/7))]) ,
            "purchased_date": winnings[0].text.strip(),
            "winning_date": winnings[7].text.strip()
        }

        return result_data
    
    def _make_search_date(self) -> dict:
        today = datetime.datetime.today()
        today_str = today.strftime("%Y%m%d")
        weekago = today - timedelta(days=7)
        weekago_str = weekago.strftime("%Y%m%d")
        return {
            "searchStartDate": weekago_str,
            "searchEndDate": today_str
        }

    def _show_result(self, body: dict) -> None:
        assert type(body) == dict

        if body.get("loginYn") != "Y":
            return

        result = body.get("result", {})
        if result.get("resultMsg", "FAILURE").upper() != "SUCCESS":    
            return