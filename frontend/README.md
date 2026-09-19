# NOVA Commerce Frontend

A polished React + Vite e-commerce frontend prototype.

## Flow

Customer → Website → Products/Menu → Cart → Checkout → Payment → Order → Admin

## Included

- Animated, responsive storefront
- Product collection and categories
- Product detail pages
- Cart with quantity controls
- Checkout details
- Payment method selection:
  - Online card
  - Cash on delivery
  - Card on delivery
- Order confirmation/tracking UI
- Admin dashboard
- Product management view
- Recent order view
- LocalStorage cart persistence

## Run

```bash
npm install
npm run dev
```

Then open the URL shown by Vite, normally:

```text
http://localhost:5173
```

## Important

This is the **frontend foundation**. The buttons and screens are wired together using local React state.

The next development stage should replace mock product/order data with a FastAPI + MongoDB backend. Payment should then be connected to a real payment provider, followed by the WhatsApp/SMS conversational ordering features from the PRD.
