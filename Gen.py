import telebot
import asyncio
import aiohttp
import threading
import re

BOT_TOKEN = "Bot Token"
bot = telebot.TeleBot(BOT_TOKEN) 
COUNTRY_FLAGS = {
    "FRANCE": "🇫🇷", "UNITED STATES": "🇺🇸", "BRAZIL": "🇧🇷", "NAMIBIA": "🇳🇦",
    "INDIA": "🇮🇳", "GERMANY": "🇩🇪", "THAILAND": "🇹🇭", "MEXICO": "🇲🇽", "RUSSIA": "🇷🇺",
}

def extract_bin(bin_input):
    match = re.match(r'(\d{6,16})', bin_input)
    if not match:
        return None
    bin_number = match.group(1)
    return bin_number.ljust(16, 'x') if len(bin_number) == 6 else bin_number

async def generate_cc_async(bin_number):
    url = f"https://drlabapis.onrender.com/api/ccgenerator?bin={bin_number}&count=10"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    raw_text = await response.text()
                    return raw_text.strip().split("\n")
                else:
                    return {"error": f"API error: {response.status}"}
    except Exception as e:
        return {"error": str(e)}

async def lookup_bin(bin_number):
    url = f"https://drlabapis.onrender.com/api/bin?bin={bin_number[:6]}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    bin_data = await response.json()
                    country_name = bin_data.get('country', 'NOT FOUND').upper()
                    return {
                        "bank": bin_data.get('issuer', 'NOT FOUND').upper(),
                        "card_type": bin_data.get('type', 'NOT FOUND').upper(),
                        "network": bin_data.get('scheme', 'NOT FOUND').upper(),
                        "tier": bin_data.get('tier', 'NOT FOUND').upper(),
                        "country": country_name,
                        "flag": COUNTRY_FLAGS.get(country_name, "🏳️")
                    }
                else:
                    return {"error": f"API error: {response.status}"}
    except Exception as e:
        return {"error": str(e)}

def format_cc_response(data, bin_number, bin_info):
    if isinstance(data, dict) and "error" in data:
        return f"❌ ERROR: {data['error']}"
    if not data:
        return "❌ NO CARDS GENERATED."

    formatted_text = f"𝗕𝗜𝗡 ⇾ <code>{bin_number[:6]}</code>\n"
    formatted_text += f"𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ <code>{len(data)}</code>\n\n"
    for card in data:
        formatted_text += f"<code>{card.upper()}</code>\n"
    formatted_text += f"\n𝗜𝗻𝗳𝗼: {bin_info.get('card_type', 'NOT FOUND')} - {bin_info.get('network', 'NOT FOUND')} ({bin_info.get('tier', 'NOT FOUND')})\n"
    formatted_text += f"𝐈𝐬𝐬𝐮𝐞𝐫: {bin_info.get('bank', 'NOT FOUND')}\n"
    formatted_text += f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'NOT FOUND')} {bin_info.get('flag', '🏳️')}"
    return formatted_text

def generate_cc(bin_number):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        cc_data = loop.run_until_complete(generate_cc_async(bin_number))
        bin_info = loop.run_until_complete(lookup_bin(bin_number))
        return format_cc_response(cc_data, bin_number, bin_info)
    except Exception as e:
        return f"❌ ERROR PROCESSING REQUEST: {e}"
    finally:
        loop.close()

@bot.message_handler(func=lambda message: message.text.startswith(("/gen", ".gen")))
def gen_command(message):
    try:
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.send_message(message.chat.id, "❌ PLEASE PROVIDE A BIN.", parse_mode="Markdown")
            return

        bin_number = extract_bin(command_parts[1])
        if not bin_number:
            bot.send_message(message.chat.id, "❌ INVALID BIN FORMAT.", parse_mode="Markdown")
            return

        
        result = generate_cc(bin_number)
        bot.send_message(message.chat.id, result, parse_mode="HTML")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ERROR: {e}")

def main():
    print("Bot Running.... Coded By @Brocode69")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"BOT POLLING ERROR: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
