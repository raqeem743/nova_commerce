import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const PRODUCTS = [
  { id: 1, name: "Apex Adjustable Bench", category: "Strength", price: 349, oldPrice: 429, rating: 4.9, badge: "BESTSELLER", emoji: "▰", description: "Commercial-grade adjustable bench with 7 back positions.", gradient: "g1" },
  { id: 2, name: "Titan Power Rack", category: "Strength", price: 899, oldPrice: 1049, rating: 4.8, badge: "PRO", emoji: "◫", description: "Heavy-duty rack engineered for serious home training.", gradient: "g2" },
  { id: 3, name: "Velocity Air Bike", category: "Cardio", price: 649, oldPrice: 749, rating: 4.9, badge: "HOT", emoji: "◉", description: "Fan-resistance cardio machine with performance console.", gradient: "g3" },
  { id: 4, name: "Orbit Rowing Machine", category: "Cardio", price: 799, oldPrice: 899, rating: 4.7, badge: "NEW", emoji: "≋", description: "Smooth magnetic resistance with a compact footprint.", gradient: "g4" },
  { id: 5, name: "Forge Olympic Barbell", category: "Accessories", price: 219, oldPrice: 259, rating: 4.8, badge: "SALE", emoji: "╫", description: "Cerakote Olympic barbell rated for demanding sessions.", gradient: "g5" },
  { id: 6, name: "Pulse Kettlebell Set", category: "Accessories", price: 189, oldPrice: 229, rating: 4.8, badge: "SET", emoji: "●", description: "Six precision-cast kettlebells for full-body workouts.", gradient: "g6" },
  { id: 7, name: "Neon Cable Station", category: "Strength", price: 1199, oldPrice: 1399, rating: 4.9, badge: "PREMIUM", emoji: "⌁", description: "Dual adjustable pulley station for unlimited exercise variety.", gradient: "g7" },
  { id: 8, name: "Core Recovery Roller", category: "Recovery", price: 79, oldPrice: 99, rating: 4.6, badge: "EASY", emoji: "○", description: "Deep-tissue recovery roller with three intensity zones.", gradient: "g8" }
];

const money = (n) => `$${n.toLocaleString()}`;

function App() {
  const [page, setPage] = useState("home");
  const [category, setCategory] = useState("All");
  const [cart, setCart] = useState(() => JSON.parse(localStorage.getItem("nova-cart") || "[]"));
  const [selected, setSelected] = useState(null);
  const [order, setOrder] = useState(null);
  const [toast, setToast] = useState("");
  const [adminTab, setAdminTab] = useState("overview");

  useEffect(() => {
    localStorage.setItem("nova-cart", JSON.stringify(cart));
  }, [cart]);

  const cartCount = cart.reduce((sum, x) => sum + x.qty, 0);
  const subtotal = cart.reduce((sum, x) => sum + x.price * x.qty, 0);
  const shipping = subtotal >= 500 || subtotal === 0 ? 0 : 29;
  const total = subtotal + shipping;

  const filtered = useMemo(
    () => category === "All" ? PRODUCTS : PRODUCTS.filter(p => p.category === category),
    [category]
  );

  const notify = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 2200);
  };

  const addToCart = (product) => {
    setCart(prev => {
      const found = prev.find(x => x.id === product.id);
      return found ? prev.map(x => x.id === product.id ? { ...x, qty: x.qty + 1 } : x) : [...prev, { ...product, qty: 1 }];
    });
    notify(`${product.name} added to cart`);
  };

  const updateQty = (id, delta) => {
    setCart(prev => prev.map(x => x.id === id ? { ...x, qty: Math.max(0, x.qty + delta) } : x).filter(x => x.qty));
  };

  const checkout = () => {
    if (!cart.length) {
      notify("Your cart is empty");
      return;
    }
    setPage("checkout");
  };

  const placeOrder = (form) => {
    const newOrder = {
      id: "NV-" + Math.floor(100000 + Math.random() * 899999),
      customer: form.name,
      email: form.email,
      method: form.payment,
      address: `${form.address}, ${form.city}`,
      items: cart,
      total,
      status: "Confirmed",
      date: new Date().toLocaleString()
    };
    setOrder(newOrder);
    setCart([]);
    setPage("order");
    notify("Order confirmed successfully");
  };

  return (
    <div className="app">
      <div className="noise" />
      <Header cartCount={cartCount} go={setPage} />
      {page === "home" && <Home go={setPage} setCategory={setCategory} />}
      {page === "shop" && (
        <Shop
          products={filtered}
          category={category}
          setCategory={setCategory}
          addToCart={addToCart}
          openProduct={(p) => { setSelected(p); setPage("product"); }}
        />
      )}
      {page === "product" && selected && (
        <Product product={selected} addToCart={addToCart} back={() => setPage("shop")} />
      )}
      {page === "cart" && (
        <Cart cart={cart} updateQty={updateQty} total={total} subtotal={subtotal} shipping={shipping} checkout={checkout} go={setPage} />
      )}
      {page === "checkout" && (
        <Checkout cart={cart} total={total} subtotal={subtotal} shipping={shipping} onSubmit={placeOrder} back={() => setPage("cart")} />
      )}
      {page === "order" && <OrderConfirmation order={order} go={setPage} />}
      {page === "admin" && (
        <Admin orders={order ? [order] : []} tab={adminTab} setTab={setAdminTab} go={setPage} />
      )}
      <Footer />
      {toast && <div className="toast">{toast}<span>✓</span></div>}
    </div>
  );
}

function Header({ cartCount, go }) {
  return (
    <header className="header">
      <button className="brand" onClick={() => go("home")}>
        <span className="brand-mark">N</span>
        <span>NOVA<span className="brand-dot">.</span></span>
      </button>
      <nav>
        <button onClick={() => go("home")}>Home</button>
        <button onClick={() => go("shop")}>Shop</button>
        <button onClick={() => go("admin")}>Admin</button>
      </nav>
      <div className="header-actions">
        <button className="icon-btn" onClick={() => go("shop")} aria-label="Search">⌕</button>
        <button className="cart-btn" onClick={() => go("cart")}>
          Cart <span>{cartCount}</span>
        </button>
      </div>
    </header>
  );
}

function Home({ go, setCategory }) {
  const jump = (cat) => { setCategory(cat); go("shop"); };
  return (
    <main>
      <section className="hero">
        <div className="hero-orb orb-a" />
        <div className="hero-orb orb-b" />
        <div className="hero-copy reveal">
          <div className="eyebrow"><i /> THE NEW STANDARD IN TRAINING</div>
          <h1>Build your<br /><em>strongest</em> self.</h1>
          <p>Premium equipment. Thoughtful design. Everything you need to turn your space into a serious training ground.</p>
          <div className="hero-buttons">
            <button className="primary" onClick={() => go("shop")}>Explore collection <b>↗</b></button>
            <button className="ghost" onClick={() => jump("Strength")}>Shop strength</button>
          </div>
          <div className="stats">
            <div><strong>4.9<span>★</span></strong><small>Customer rating</small></div>
            <div><strong>48K+</strong><small>Athletes equipped</small></div>
            <div><strong>2–5d</strong><small>Fast delivery</small></div>
          </div>
        </div>
        <div className="hero-art reveal delay">
          <div className="art-ring ring-1" />
          <div className="art-ring ring-2" />
          <div className="equipment">
            <div className="rack-top" />
            <div className="rack-left" />
            <div className="rack-right" />
            <div className="bench-seat" />
            <div className="bench-back" />
            <div className="bench-leg" />
            <div className="plate plate-a" />
            <div className="plate plate-b" />
            <div className="bar" />
          </div>
          <div className="floating-card fc-top"><span>01</span><b>ENGINEERED<br />TO PERFORM</b></div>
          <div className="floating-card fc-bottom"><b>FREE SHIPPING</b><span>orders over $500</span></div>
        </div>
      </section>

      <section className="marquee">
        <div>PRECISION <span>✦</span> PERFORMANCE <span>✦</span> DURABILITY <span>✦</span> PRECISION <span>✦</span> PERFORMANCE <span>✦</span> DURABILITY <span>✦</span></div>
      </section>

      <section className="section collection">
        <div className="section-head">
          <div><span className="eyebrow">CURATED FOR YOU</span><h2>Train without<br /><em>compromise.</em></h2></div>
          <button className="text-link" onClick={() => go("shop")}>View all products ↗</button>
        </div>
        <div className="category-grid">
          <CategoryCard title="Strength" number="01" visual="strength" onClick={() => jump("Strength")} />
          <CategoryCard title="Cardio" number="02" visual="cardio" onClick={() => jump("Cardio")} />
          <CategoryCard title="Accessories" number="03" visual="accessories" onClick={() => jump("Accessories")} />
        </div>
      </section>

      <section className="section feature-band">
        <div className="feature-copy"><span className="eyebrow">WHY NOVA</span><h2>Less noise.<br /><em>More focus.</em></h2><p>Every piece is selected around one idea: remove distractions and make training feel effortless.</p></div>
        <div className="feature-list">
          <Feature n="01" title="Built for years" text="Commercial-grade materials without commercial-grade complexity." />
          <Feature n="02" title="Designed to fit" text="Clean silhouettes and compact footprints for modern spaces." />
          <Feature n="03" title="Support that stays" text="Real people, clear warranties and fast delivery when you need it." />
        </div>
      </section>
    </main>
  );
}

function CategoryCard({ title, number, visual, onClick }) {
  return <button className={`category-card ${visual}`} onClick={onClick}>
    <span className="cat-num">{number}</span><div className="cat-visual">{visual === "strength" ? "▰" : visual === "cardio" ? "◉" : "╫"}</div><div className="cat-bottom"><h3>{title}</h3><span>Explore ↗</span></div>
  </button>;
}

function Feature({ n, title, text }) {
  return <div className="feature-item"><span>{n}</span><div><h3>{title}</h3><p>{text}</p></div><b>+</b></div>;
}

function Shop({ products, category, setCategory, addToCart, openProduct }) {
  const cats = ["All", "Strength", "Cardio", "Accessories", "Recovery"];
  return <main className="shop-page">
    <section className="shop-heading"><span className="eyebrow">THE COLLECTION</span><h1>Equipment that<br /><em>earns its place.</em></h1><p>Professional performance, residential footprint.</p></section>
    <div className="filter-row">{cats.map(c => <button key={c} className={category === c ? "active" : ""} onClick={() => setCategory(c)}>{c}</button>)}</div>
    <section className="product-grid">{products.map(p => <ProductCard key={p.id} p={p} add={addToCart} open={openProduct} />)}</section>
  </main>;
}

function ProductCard({ p, add, open }) {
  return <article className="product-card">
    <button className={`product-visual ${p.gradient}`} onClick={() => open(p)}>
      <span className="badge">{p.badge}</span><span className="product-symbol">{p.emoji}</span><span className="view-pill">View ↗</span>
    </button>
    <div className="product-info">
      <div><small>{p.category}</small><h3>{p.name}</h3></div>
      <div className="rating">★ {p.rating}</div>
    </div>
    <p className="product-desc">{p.description}</p>
    <div className="product-buy"><div><strong>{money(p.price)}</strong><del>{money(p.oldPrice)}</del></div><button onClick={() => add(p)}>+ Add</button></div>
  </article>;
}

function Product({ product, addToCart, back }) {
  return <main className="detail-page">
    <button className="back" onClick={back}>← Back to collection</button>
    <div className="detail-grid">
      <div className={`detail-visual ${product.gradient}`}><span className="product-symbol huge">{product.emoji}</span></div>
      <div className="detail-copy"><span className="eyebrow">{product.category} / {product.badge}</span><h1>{product.name}</h1><div className="detail-rating">★ {product.rating} <span>128 reviews</span></div><p>{product.description} Built for athletes who expect dependable performance, clean mechanics and a premium finish.</p><div className="detail-price">{money(product.price)} <del>{money(product.oldPrice)}</del></div><button className="primary wide" onClick={() => addToCart(product)}>Add to cart <b>＋</b></button><div className="trust-row"><span>✓ Secure checkout</span><span>✓ 30-day returns</span><span>✓ 2-year warranty</span></div></div>
    </div>
  </main>;
}

function Cart({ cart, updateQty, subtotal, shipping, total, checkout, go }) {
  return <main className="checkout-page">
    <div className="page-title"><span className="eyebrow">YOUR CART</span><h1>Ready when<br /><em>you are.</em></h1></div>
    {!cart.length ? <div className="empty"><div>◌</div><h2>Your cart is empty</h2><p>Add something worth training for.</p><button className="primary" onClick={() => go("shop")}>Browse equipment ↗</button></div> :
    <div className="cart-layout"><div className="cart-items">{cart.map(x => <div className="cart-item" key={x.id}><div className={`mini-visual ${x.gradient}`}>{x.emoji}</div><div className="cart-main"><small>{x.category}</small><h3>{x.name}</h3><div className="qty"><button onClick={() => updateQty(x.id, -1)}>−</button><b>{x.qty}</b><button onClick={() => updateQty(x.id, 1)}>+</button></div></div><strong>{money(x.price * x.qty)}</strong></div>)}</div>
      <Summary subtotal={subtotal} shipping={shipping} total={total} button="Checkout →" onClick={checkout} /></div>}
  </main>;
}

function Summary({ subtotal, shipping, total, button, onClick }) {
  return <aside className="summary"><span className="eyebrow">ORDER SUMMARY</span><div><span>Subtotal</span><b>{money(subtotal)}</b></div><div><span>Shipping</span><b>{shipping ? money(shipping) : "FREE"}</b></div><hr /><div className="total-line"><span>Total</span><strong>{money(total)}</strong></div><button className="primary wide" onClick={onClick}>{button}</button><small className="secure">⌁ Secure & encrypted checkout</small></aside>;
}

function Checkout({ cart, subtotal, shipping, total, onSubmit, back }) {
  const [form, setForm] = useState({ name: "", email: "", address: "", city: "", phone: "", payment: "online_card" });
  const [step, setStep] = useState(1);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const next = (e) => { e.preventDefault(); if (step < 2) setStep(2); else onSubmit(form); };
  return <main className="checkout-page">
    <button className="back" onClick={back}>← Cart</button>
    <div className="page-title compact"><span className="eyebrow">CHECKOUT</span><h1>Finish your<br /><em>order.</em></h1></div>
    <div className="steps"><span className="done">01 Details</span><i /> <span className={step === 2 ? "done" : ""}>02 Payment</span><i /> <span>03 Confirmation</span></div>
    <form className="checkout-layout" onSubmit={next}>
      <div className="form-card">
        {step === 1 ? <>
          <h2>Delivery details</h2><p className="muted">Where should we send your equipment?</p>
          <div className="form-grid"><label>Full name<input required value={form.name} onChange={e => set("name", e.target.value)} placeholder="Alex Morgan" /></label><label>Phone<input required value={form.phone} onChange={e => set("phone", e.target.value)} placeholder="+92 300 0000000" /></label><label className="full">Email address<input required type="email" value={form.email} onChange={e => set("email", e.target.value)} placeholder="alex@example.com" /></label><label className="full">Address<input required value={form.address} onChange={e => set("address", e.target.value)} placeholder="House / street / area" /></label><label>City<input required value={form.city} onChange={e => set("city", e.target.value)} placeholder="Lahore" /></label><label>Postcode<input required placeholder="54000" /></label></div>
        </> : <>
          <h2>Payment method</h2><p className="muted">Choose how you want to pay.</p>
          <div className="payment-options">{[["online_card","Card online","Secure hosted payment"],["cash_on_delivery","Cash on delivery","Pay when your order arrives"],["card_on_delivery","Card on delivery","Pay by card to the driver"]].map(([v,t,d]) => <button type="button" key={v} className={form.payment === v ? "payment-option selected" : "payment-option"} onClick={() => set("payment", v)}><span className="radio">{form.payment === v ? "●" : ""}</span><div><b>{t}</b><small>{d}</small></div><span>›</span></button>)}</div>
          <div className="payment-note">🔒 Your payment details are handled securely. NOVA never stores your card number.</div>
        </>}
        <button className="primary wide" type="submit">{step === 1 ? "Continue to payment →" : "Place order • " + money(total)}</button>
      </div>
      <Summary subtotal={subtotal} shipping={shipping} total={total} button="Items secured ✓" onClick={() => {}} />
    </form>
  </main>;
}

function OrderConfirmation({ order, go }) {
  return <main className="order-page"><div className="success-mark">✓</div><span className="eyebrow">ORDER CONFIRMED</span><h1>You're officially<br /><em>in motion.</em></h1><p>Thanks, {order?.customer || "athlete"}. Your order has been received and is moving to fulfillment.</p><div className="order-card"><div><small>ORDER NUMBER</small><strong>{order?.id}</strong></div><div><small>PAYMENT</small><strong>{order?.method?.replaceAll("_", " ")}</strong></div><div><small>TOTAL</small><strong>{money(order?.total || 0)}</strong></div></div><div className="order-track"><span className="active">✓<small>Placed</small></span><i /><span>2<small>Processing</small></span><i /><span>3<small>Dispatch</small></span><i /><span>4<small>Delivered</small></span></div><button className="primary" onClick={() => go("shop")}>Continue shopping ↗</button></main>;
}

function Admin({ orders, tab, setTab, go }) {
  const totalSales = orders.reduce((s, o) => s + o.total, 0);
  return <main className="admin-page">
    <div className="admin-top"><div><span className="eyebrow">NOVA CONTROL</span><h1>Operations<br /><em>dashboard.</em></h1></div><button className="ghost" onClick={() => go("shop")}>View storefront ↗</button></div>
    <div className="admin-tabs">{["overview","orders","products"].map(t => <button className={tab === t ? "active" : ""} onClick={() => setTab(t)} key={t}>{t}</button>)}</div>
    {tab === "overview" && <><div className="metrics"><Metric label="Revenue" value={money(totalSales || 12480)} trend="+18.4%" /><Metric label="Orders" value={orders.length || "24"} trend="+12.1%" /><Metric label="Avg. order" value={money(orders[0]?.total || 520)} trend="+4.7%" /><Metric label="Customers" value="186" trend="+9.2%" /></div><div className="admin-grid"><div className="panel"><div className="panel-head"><h2>Recent orders</h2><button onClick={() => setTab("orders")}>View all →</button></div><OrderTable orders={orders} /></div><div className="panel"><div className="panel-head"><h2>Order flow</h2></div><div className="flow-bars"><div><span>Website</span><b style={{width:"88%"}} /></div><div><span>WhatsApp</span><b style={{width:"63%"}} /></div><div><span>SMS</span><b style={{width:"38%"}} /></div></div><div className="automation"><span className="live-dot" /> Automation ready <small>Review exceptions only</small></div></div></div></>}
    {tab === "orders" && <div className="panel"><div className="panel-head"><h2>Orders</h2><span className="muted">All channels</span></div><OrderTable orders={orders} /></div>}
    {tab === "products" && <div className="panel"><div className="panel-head"><h2>Products</h2><span className="muted">{PRODUCTS.length} active products</span></div><div className="admin-products">{PRODUCTS.map(p => <div key={p.id}><span className={`mini-visual ${p.gradient}`}>{p.emoji}</span><b>{p.name}</b><span>{money(p.price)}</span><em>Active</em></div>)}</div></div>}
  </main>;
}

function Metric({ label, value, trend }) { return <div className="metric"><small>{label}</small><strong>{value}</strong><span>↗ {trend}</span></div>; }
function OrderTable({ orders }) { return <div className="table"><div className="tr th"><span>Order</span><span>Customer</span><span>Total</span><span>Status</span></div>{(orders.length ? orders : [{id:"NV-829431",customer:"Sarah Khan",total:749,status:"Confirmed"},{id:"NV-829430",customer:"Hamza Ali",total:1299,status:"Processing"},{id:"NV-829429",customer:"Daniel Reed",total:349,status:"Delivered"}]).map(o => <div className="tr" key={o.id}><span>#{o.id}</span><span>{o.customer}</span><span>{money(o.total)}</span><span className="status">{o.status}</span></div>)}</div>; }

function Footer() {
  return <footer><div className="footer-brand"><span className="brand-mark">N</span><b>NOVA.</b><p>Performance equipment<br />for people who mean it.</p></div><div><small>EXPLORE</small><a>Shop</a><a>Collections</a><a>New arrivals</a></div><div><small>COMPANY</small><a>About</a><a>Support</a><a>Shipping</a></div><div><small>FOLLOW</small><a>Instagram ↗</a><a>Facebook ↗</a><a>WhatsApp ↗</a></div><div className="footer-bottom">© 2026 NOVA. All rights reserved. <span>Built for the next rep.</span></div></footer>;
}

createRoot(document.getElementById("root")).render(<App />);
