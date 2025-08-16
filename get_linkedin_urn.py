import requests

APP_ID = "1256805452306263"
APP_SECRET = "247a6bf59b176b1e4d0ecda08f3b06b9"
SHORT_LIVED_TOKEN = "EAAR3DtKJV1cBPMm28r5CsC0hCjhiFRPo9E94oX5pWOXSlZBO7ZCpPF9vELSff4ZCiYE4LrOm4XxthEWB2oznSj670w3WwKBLBwTZCFx1SpcAyOi8RkKNy8WajIUH0A3R8M84b7cxccRCKZALXIxcAb9zSLhTRUHkR33q7hW3uPK5Y2qhsiNwHC5toW6DcwmhnPpsKAEeALhte4FVZA3WTcv3i9lH2mn52jUjgZCr3YZD"

url = f"https://graph.facebook.com/v21.0/oauth/access_token"
params = {
    "grant_type": "fb_exchange_token",
    "client_id": APP_ID,
    "client_secret": APP_SECRET,
    "fb_exchange_token": SHORT_LIVED_TOKEN
}

response = requests.get(url, params=params).json()
print(response)
# => {"access_token": "long_lived_token", "token_type": "bearer", "expires_in": 5183944}
