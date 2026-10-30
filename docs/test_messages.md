# Munim AI — Test Messages

Use these to test the bot end-to-end. Send from a number that is NOT the owner/business number.

---

## TEXT MESSAGES (send as-is on WhatsApp)

### 🛒 Orders (simple)
```
1.  2 kurti chahiye medium mein, pink wali
2.  bhaiya ek blue kurti size L mein milegi?
3.  mujhe 3 suits chahiye, white medium aur black large
4.  ek set chahiye anarkali ka, size S, price kya hai?
5.  do pieces chahiye M size mein
```

### 🛒 Orders (Hinglish, conversational)
```
6.  hi, mujhe vo wali kurti dikhao jo aapne last time dali thi stories pe, vo chahiye mujhe ek
7.  bhai kal tak mil sakti hai kya? 2 kurti chahiye urgent, medium size, koi bhi light colour
8.  yaar meri friend ke liye leni hai gift mein, anarkali XL mein, blue ya purple
9.  set mil sakta hai? top aur palazzo dono, M size
10. order karna tha — pink kurti L mein, price confirm karo pehle
```

### 💸 Payments (text only)
```
11. payment kar di hai, check karo
12. 599 bheja abhi BHIM se
13. bhaiya UPI se 1200 bheja, naam se check karo
14. done, paid 450
15. transfer ho gaya, screenshot bhejti hoon
```

### 💸 Partial payments
```
16. 200 advance de rahi hoon, baaki delivery pe
17. abhi 500 bhejti hoon, 300 baad mein
```

### ❓ Questions — general
```
18. kab milega mera order?
19. delivery kitne din mein hoti hai?
20. COD hota hai kya?
21. return policy kya hai?
22. kya aap Delhi deliver karti ho?
```

### ❓ Catalog queries
```
23. kurti ke kya kya sizes available hain?
24. XL mein kuch hai kya aapke paas?
25. price range kya hai kurtiyon ki?
26. koi new collection aayi hai kya?
```

### 😤 Complaints
```
27. bhaiya galat size aa gaya, maine M manga tha L aaya
28. kurti ki stitching kharab hai, loose thread hai
29. refund karna hai, nahi pasand aayi
30. parcel damage tha jab mila
```

### 🤖 Owner commands (send from OWNER number only)
```
31. summary
32. pending dues
33. #private   (first word of message, stops bot for that customer)
34. #resume    (restarts bot for that customer)
```

### 🗑️ Gibberish / out-of-scope (bot should reply politely or ignore)
```
35. hahahaha okay
36. 👍
37. okay
38. ?
39. kal baat karte hain
40. (empty audio / sticker)
```

---

## AUDIO MESSAGES — Record These Yourself 🎙️

You need to record these as WhatsApp voice notes. Speak naturally in Hinglish.

| # | What to say (bolne ka script) | Expected AI output |
|---|---|---|
| A1 | *"Do kurti chahiye mujhe, medium size mein, pink colour. Aur bataao price kya hai?"* | type: order + catalog_query |
| A2 | *"Bhaiya payment kar di hai, BHIM se, check karo please — paanch sau rupaye bheje hain"* | type: payment, amount: 500 |
| A3 | *"Yaar kab aayega mera order? Kal order kiya tha, aaj delivery thi na?"* | type: delivery_query |
| A4 | *"Galat size aa gaya, XL bhej diya, maine L manga tha. Kya return ho sakta hai?"* | type: complaint |
| A5 | *Mumbled/fast Hinglish: "haan vo wali leni thi... medium... kitna tha?"* | confidence low → escalate |

> **Tip:** Record in a slightly noisy room for one or two — tests real-world Whisper/Gemini audio accuracy.

---

## UPI SCREENSHOTS — Take/Mock These Yourself 📸

You need real or realistic-looking screenshots. Here's what each should show:

| # | Screenshot content | Expected AI output |
|---|---|---|
| U1 | BHIM / GPay success screen — ₹599 paid to business name | type: payment, amount: 599 |
| U2 | PhonePe success — ₹1200, with UPI transaction ID visible | type: payment, amount: 1200, upi_txn_id extracted |
| U3 | Partial — ₹200 "sent" screen, rest of chat says "baaki baad mein" | type: partial_payment, amount: 200 |
| U4 | Low-res / blurry screenshot (hard to read amount) | confidence.amount low → escalate |
| U5 | Handwritten notebook photo — "Priya – 2 kurti M – ₹599 – pending" | type: order, manual ledger entry |

> **Tip for U5:** Write it on paper and photograph it. Tests Gemini's handwriting OCR — a key differentiator.

---

## Testing Checklist

- [ ] Echo bot: does every text message get a reply?
- [ ] AI extraction: does each message return correct `type`?
- [ ] Sheet update: does each order/payment create a new row?
- [ ] Low-confidence: does owner get pinged on unclear messages?
- [ ] Audio A5: does mumbled audio escalate correctly?
- [ ] Screenshot U4: does blurry image trigger low confidence?
- [ ] `#private`: does the bot stop replying after owner sends this?
- [ ] Owner `summary` command: does bot reply with summary?

