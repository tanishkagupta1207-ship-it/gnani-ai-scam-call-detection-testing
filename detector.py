import re
_OTP = r"(?:\botp\b|\bo\s*\.?\s*t\s*\.?\s*p\b|ओ\s*\.?\s*टी\s*\.?\s*पी|one time password|वन\s*टाइम\s*पासवर्ड|verification code|वेरिफिकेशन\s*कोड|\bcvv\b|सी\s*वी\s*वी|\bpin\b|पिन|\bcode\b|कोड)"
_ASK = r"(?:बता\s*(?:दो|दीजिए|दीजिये|दें|दे|ना)|बताओ|बताइए|बोलो|बोल\s*दो|भेज\s*(?:दो|दीजिए|दीजिये|दें)|भेजो|शेयर|bata\s*(?:do|dijiye|dena|de)\b|batao|bhej\s*(?:do|dijiye)|bhejo|share|send|tell|read\s*out|give)"
# Five scam-script signals, matched in both Roman and Devanagari script
# (Prisma's API output uses Devanagari by default).
SIGNALS = {
    "Official impersonation": r"\bcbi\b|सी\s*बी\s*आई|police|पुलिस|customs|कस्टम|\btrai\b|ट्राई|narcotics|नारकोटिक्स|inspector|इंस्पेक्टर|officer|ऑफिसर",
    "Arrest or legal threat": r"arrest|अरेस्ट|गिरफ्तार|warrant|वारंट|illegal|इल्लीगल|अवैध|\bcase\b|केस|\bjail\b|जेल",
    "Secrecy / stay on call": r"kisi ko mat|किसी को मत|mat bata|मत बता|line par bane|लाइन पर बने|call par bane|कॉल पर बने|call mat kat|कॉल मत काट|video call|वीडियो कॉल",
    "Payment demand": r"rupaye|rupees|rupay|रुपये|रुपए|रुपया|transfer|ट्रांसफर|\bupi\b|यूपीआई",
    "OTP / code request": rf"{_OTP}.{{0,40}}?{_ASK}|{_ASK}.{{0,40}}?{_OTP}",
}

MESSAGES = {
    "scam": "यह स्कैम हो सकता है। कॉल काट दीजिए और 1930 पर कॉल कीजिए।",
    "suspicious": "सावधान रहिए। फ़ोन पर कभी OTP या पैसे मत भेजिए। OTP सिर्फ़ तभी बताइए जब डिलीवरी वाला या ड्राइवर आपके सामने खड़ा हो।",
}

def find_amount(t):
    if re.search(r"\d+\.?\s+\d{1,3},\d{3}", t):  # garbled, e.g. "50. 10,000"
        return "unclear"
    m = re.search(r"(\d[\d,]*)\s*(?:rupaye|rupees|rupay|रुपये|रुपए|rs\b)", t)
    if m:
        return m.group(1)
    m = re.search(r"(\S+\s+(?:हज़ार|हजार|hazaar|hazar|thousand|लाख|lakh))", t)
    return m.group(1) if m else "unclear"

def analyze(text):
    t = text.lower()
    hits, spans = {}, []
    for name, p in SIGNALS.items():
        found = list(re.finditer(p, text, re.IGNORECASE))
        hits[name] = bool(found)
        spans += [(m.start(), m.end(), name) for m in found]
    spans.sort()
    clean, end = [], 0
    for a, b, n in spans:  # drop overlaps so the page can highlight safely
        if a >= end:
            clean.append([a, b, n]); end = b
    n = sum(hits.values())
    otp = hits["OTP / code request"]
    if n >= 3 or (otp and n >= 2):
       label = "scam"
    elif otp or n == 2:
       label = "suspicious"
    else:
       label = "none"
    return {"label": label, "signals": hits, "amount": find_amount(t), "spans": clean}