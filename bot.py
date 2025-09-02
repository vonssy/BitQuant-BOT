from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    BasicAuth
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from base58 import b58decode, b58encode
from nacl.signing import SigningKey
from datetime import datetime, timezone
from colorama import *
import asyncio, random, json, re, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class BitQuant:
    def __init__(self) -> None:
        self.BASE_API = "https://quant-api.opengradient.ai/api"
        self.PAGE_URL = "https://www.bitquant.io/"
        self.SITE_KEY = "0x4AAAAAABRnkPBT6yl0YKs1"
        self.CAPTCHA_KEY = None
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.access_tokens = {}
        self.id_tokens = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}BitQuant {Fore.BLUE + Style.BRIGHT}Auto BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def load_2captcha_key(self):
        try:
            with open("2captcha_key.txt", 'r') as file:
                captcha_key = file.read().strip()

            return captcha_key
        except Exception as e:
            return None
    
    def load_question_lists(self):
        filename = "question_lists.json"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED}File {filename} Not Found.{Style.RESET_ALL}")
                return

            with open(filename, 'r') as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
                return []
        except json.JSONDecodeError:
            return []
    
    async def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy)
            return connector, None, None

        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy, None

        raise Exception("Unsupported Proxy Type.")

    def generate_address(self, account: str):
        try:
            decode_account = b58decode(account)
            signing_key = SigningKey(decode_account[:32])
            verify_key = signing_key.verify_key
            address = b58encode(verify_key.encode()).decode()
            
            return address
        except Exception as e:
            return None

    def generate_payload(self, account: str, address: str):
        try:
            now = datetime.now(timezone.utc)
            nonce = int(now.timestamp() * 1000)
            issued_at = now.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            message = f"bitquant.io wants you to sign in with your **blockchain** account:\n{address}\n\nURI: https://bitquant.io\nVersion: 1\nChain ID: solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp\nNonce: {nonce}\nIssued At: {issued_at}"
            
            decode_account = b58decode(account)
            signing_key = SigningKey(decode_account[:32])
            encode_message = message.encode('utf-8')
            signature = signing_key.sign(encode_message)
            signature_base58 = b58encode(signature.signature).decode()

            payload = {
                "address": address,
                "message": message,
                "signature": signature_base58
            }
            
            return payload
        except Exception as e:
            raise Exception(f"Generate Req Payload Failed {str(e)}")
        
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None

    def generate_agent_payload(self, address: str, turnstile_token: str, question: str):
        try:
            payload = {
                "context":{
                    "conversationHistory": [
                        { "type":"user", "message":question },
                        { "type":"user", "message":question }
                    ],
                    "address":address,
                    "poolPositions":[],
                    "availablePools":[]
                },
                "message":{ "type":"user", "message":question },
                "captchaToken":turnstile_token
            }

            return payload
        except Exception as e:
            return None
        
    async def print_timer(self):
        for remaining in range(random.randint(5, 10), 0, -1):
            print(
                f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Wait For{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {remaining} {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Seconds For Next Interaction...{Style.RESET_ALL}",
                end="\r",
                flush=True
            )
            await asyncio.sleep(1)
        
    def print_question(self):
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxyscrape Free Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run With Private Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}3. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2/3] -> {Style.RESET_ALL}").strip())

                if proxy_choice in [1, 2, 3]:
                    proxy_type = (
                        "With Proxyscrape Free" if proxy_choice == 1 else 
                        "With Private" if proxy_choice == 2 else 
                        "Without"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1, 2 or 3.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1, 2 or 3).{Style.RESET_ALL}")

        rotate_proxy = False
        if proxy_choice in [1, 2]:
            while True:
                rotate_proxy = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()

                if rotate_proxy in ["y", "n"]:
                    rotate_proxy = rotate_proxy == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

        return proxy_choice, rotate_proxy
    
    async def check_connection(self, proxy_url=None):
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Connection Not 200 OK {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
        
        return None
    
    async def solve_cf_turnstile(self, retries=5):
        for attempt in range(retries):
            try:
                async with ClientSession(timeout=ClientTimeout(total=60)) as session:

                    if self.CAPTCHA_KEY is None:
                        return None
                    
                    url = f"http://2captcha.com/in.php?key={self.CAPTCHA_KEY}&method=turnstile&sitekey={self.SITE_KEY}&pageurl={self.PAGE_URL}"
                    async with session.get(url=url) as response:
                        response.raise_for_status()
                        result = await response.text()

                        if 'OK|' not in result:
                            await asyncio.sleep(5)
                            continue

                        request_id = result.split('|')[1]

                        self.log(
                            f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                            f"{Fore.BLUE+Style.BRIGHT}Req Id  :{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {request_id} {Style.RESET_ALL}"
                        )

                        for _ in range(30):
                            res_url = f"http://2captcha.com/res.php?key={self.CAPTCHA_KEY}&action=get&id={request_id}"
                            async with session.get(url=res_url) as res_response:
                                res_response.raise_for_status()
                                res_result = await res_response.text()

                                if 'OK|' in res_result:
                                    turnstile_token = res_result.split('|')[1]
                                    return turnstile_token
                                elif res_result == "CAPCHA_NOT_READY":
                                    self.log(
                                        f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                                        f"{Fore.BLUE+Style.BRIGHT}Message :{Style.RESET_ALL}"
                                        f"{Fore.YELLOW + Style.BRIGHT} Captcha Not Ready {Style.RESET_ALL}"
                                    )
                                    await asyncio.sleep(5)
                                    continue
                                else:
                                    break

            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                return None
    
    async def user_login(self, account: str, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/verify/solana"
        data = json.dumps(self.generate_payload(account, address))
        headers = {
            **self.HEADERS[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Login Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
        
    async def secure_token(self, address: str, proxy_url=None, retries=5):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=AIzaSyBDdwO2O_Ose7LICa-A78qKJUCEE3nAwsM"
        data = json.dumps({"token":self.access_tokens[address], "returnSecureToken":True})
        headers = {
            **self.HEADERS[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Fetch Id Token Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def user_stats(self, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/activity/stats?address={address}"
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.id_tokens[address]}"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Fetch Activity Stats Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def run_agent(self, address: str, turnstile_token: str, question: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/v2/agent/run"
        data = json.dumps(self.generate_agent_payload(address, turnstile_token, question))
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.id_tokens[address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}    Status    :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Interaction Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
    
    async def process_check_connection(self, address: str, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy  :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {proxy} {Style.RESET_ALL}"
            )

            is_valid = await self.check_connection(proxy)
            if not is_valid:
                if rotate_proxy:
                    proxy = self.rotate_proxy_for_account(address)

                continue

            return True
            
    async def process_user_login(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        is_valid = await self.process_check_connection(address, use_proxy, rotate_proxy)
        if is_valid:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None

            login = await self.user_login(account, address, proxy)
            if login:
                self.access_tokens[address] = login["token"]
                return True
            
            return False
        
    async def process_secure_token(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        logined = await self.process_user_login(account, address, use_proxy, rotate_proxy)
        if logined:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None

            id_token = await self.secure_token(address, proxy)
            if id_token:
                self.id_tokens[address] = id_token["idToken"]

                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Login Success {Style.RESET_ALL}"
                )
                return True
            
            return False

    async def process_accounts(self, account: str, address: str, questions: list, use_proxy: bool, rotate_proxy: bool):
        secured = await self.process_secure_token(account, address, use_proxy, rotate_proxy)
        if secured:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None

            stats = await self.user_stats(address, proxy)
            if not stats:
                return

            points = stats.get("points", 0)
            message_count = stats.get("message_count", 0)
            
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Balance:{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {points} PTS {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Message:{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {message_count} {Style.RESET_ALL}"
            )

            daily_message_count = stats.get("daily_message_count", 0)
            daily_message_limit = stats.get("daily_message_limit", 0)

            if daily_message_count >= daily_message_limit:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Agents :{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Daily Interactions Reached {Style.RESET_ALL}"
                )
                return
            
            self.log(f"{Fore.CYAN+Style.BRIGHT}Captcha:{Style.RESET_ALL}")
            self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                f"{Fore.YELLOW + Style.BRIGHT}Solving Captcha Turnstile{Style.RESET_ALL}"
            )
            
            turnstile_token = await self.solve_cf_turnstile()
            if not turnstile_token:
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Captcha Turnstile Not Solved {Style.RESET_ALL}"
                )
                return
            
            self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                f"{Fore.BLUE+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.GREEN + Style.BRIGHT} Captcha Turnstile Solved Successfully {Style.RESET_ALL}"
            )

            used_questions = set()

            while daily_message_count < daily_message_limit:
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Interactions{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} {daily_message_count + 1} of {daily_message_limit} {Style.RESET_ALL}                       "
                )

                available_questions = [question for question in questions if question not in used_questions]

                question = random.choice(available_questions)

                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}    Question  : {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{question}{Style.RESET_ALL}"
                )

                run = await self.run_agent(address, turnstile_token, question, proxy)
                if run:
                    answer = run.get("message", "Unknown")

                    self.log(
                        f"{Fore.CYAN + Style.BRIGHT}    Status    :{Style.RESET_ALL}"
                        f"{Fore.GREEN + Style.BRIGHT} Interaction Success {Style.RESET_ALL}"
                    )
                    self.log(
                        f"{Fore.CYAN + Style.BRIGHT}    Answer    : {Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT}{answer}{Style.RESET_ALL}"
                    )

                used_questions.add(question)
                daily_message_count += 1

                await self.print_timer()
                    
    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            capctha_key = self.load_2captcha_key()
            if capctha_key:
                self.CAPTCHA_KEY = capctha_key
            
            proxy_choice, rotate_proxy = self.print_question()

            questions = self.load_question_lists()
            if not questions:
                self.log(f"{Fore.RED + Style.BRIGHT}No Questions Loaded.{Style.RESET_ALL}")
                return

            while True:
                use_proxy = True if proxy_choice == 1 else False

                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                if use_proxy:
                    await self.load_proxies()
                
                separator = "=" * 23
                for account in accounts:
                    if account:
                        address = self.generate_address(account)
                        self.log(
                            f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                        )

                        if not address:
                            self.log(
                                f"{Fore.CYAN + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                                f"{Fore.RED + Style.BRIGHT} Invalid Private Key or Library Version Not Supported {Style.RESET_ALL}"
                            )
                            continue

                        self.HEADERS[address] = {
                            "Accept": "*/*",
                            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Origin": "https://www.bitquant.io",
                            "Referer": "https://www.bitquant.io/",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "cross-site",
                            "User-Agent": FakeUserAgent().random
                        }

                        await self.process_accounts(account, address, questions, use_proxy, rotate_proxy)
                        await asyncio.sleep(3)

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*68)
                seconds = 24 * 60 * 60
                while seconds > 0:
                    formatted_time = self.format_seconds(seconds)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    seconds -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
            return
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        bot = BitQuant()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] BitQuant - BOT{Style.RESET_ALL}                                       "                              
        )