# Monetization — Jnana Setu

## Tier structure

### Free tier
- 3 queries per day
- Daily reflection (always free)
- Full book explorer
- English responses only
- Citation titles visible, no excerpt

### Premium (₹299/month or $4/month)
- Unlimited queries
- English + Hindi responses
- Full citation excerpts
- Export chat as PDF
- Early access to new features

### Scholar (₹999/month or $12/month)
- Everything in Premium
- API access (100 calls/day)
- "Ask about a specific book" mode
- Guided 30-day spiritual study plans
- Priority query queue

### Institutional (₹4999/month — temples, pathshalas)
- Unlimited API access
- White-label embed widget
- Custom Acharya corpus (add your Guru's books)
- Analytics dashboard
- Dedicated support

---

## Revenue streams

1. **Subscriptions** — primary revenue, via Razorpay (India) + Stripe (international)
2. **API licensing** — for Jain community apps and temple websites
3. **Sponsored "book of the month"** — Jain publishers pay for featured placement
4. **Digital study circles** — monthly webinars with AI-powered Q&A (₹199/session)
5. **Custom AI study plans** — one-time purchase (₹499) for 30-day plan

---

## Implementation notes

### Payment integration
```
Razorpay (India): razorpay.com
Stripe (international): stripe.com

Backend: POST /billing/subscribe
         POST /billing/cancel
         Webhook handler for payment events
```

### Feature gating
```python
# middleware.py
def check_tier_limit(user: User, feature: str) -> bool:
    if feature == "query":
        if user.tier == "free" and user.queries_today >= 3:
            raise HTTPException(429, "Daily limit reached")
    if feature == "hindi_response":
        if user.tier == "free":
            raise HTTPException(403, "Hindi responses require Premium")
    return True
```

### Analytics to track
- Daily active users
- Queries per session
- Most queried authors
- Most queried Anuyoga category
- Free-to-premium conversion rate
- Query quality score (thumbs up/down)

---

## Content marketing (driving traffic)

1. **YouTube channel:** Weekly "What does Jainism say about X?" videos
   - Use the chatbot live on screen
   - Each video answers one modern life question through Jain texts
   - Target: career stress, relationships, materialism, death, diet

2. **Instagram / Reels:** Daily sutra card
   - Auto-generate from `/daily-reflection` endpoint
   - Branded with Jnana Setu watermark

3. **SEO:** Blog posts generated from the RAG system
   - "What Acharya Vidyasagar Ji says about X"
   - "Muni Tarun Sagar Ji on Y"
   - Long-tail Jain philosophy queries

4. **WhatsApp bot:** Free daily reflection via WhatsApp Business API
   - Entry point for free users → upgrade to full app
