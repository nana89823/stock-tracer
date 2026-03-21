# Stock Tracer Landing Page Design Spec

## Goal

Build a professional, clean, modern Landing Page for Stock Tracer as the public-facing homepage (`/`). The page should communicate the product's value to all audiences (散戶、進階投資人、團隊展示) and guide visitors toward registration/login.

## Architecture

The Landing Page is a standalone page at the root route (`/`), accessible without authentication. The existing dashboard moves from `/(dashboard)/page.tsx` (currently served at `/`) to a new sub-path `/home`.

### Route Changes

| Before | After | Notes |
|--------|-------|-------|
| `/` → dashboard (via `(dashboard)/page.tsx`) | `/` → Landing Page (`/app/page.tsx`) | New file |
| `/welcome` → simple landing | Deleted | Replaced by `/` |
| `/(dashboard)/*` → dashboard pages | Unchanged | Still protected by AuthGuard |

**Key insight:** Since `(dashboard)` is a route group, its pages are served at `/`, `/stocks/[id]`, `/backtests`, etc. Adding a root `/app/page.tsx` will take precedence over `/(dashboard)/page.tsx` for the `/` route. The dashboard homepage needs to move to a non-conflicting path.

### Route Resolution Strategy

Move dashboard home to `/(dashboard)/home/page.tsx` so it's served at `/home`.

Updated routes:
- `/` → Landing Page (public)
- `/home` → Dashboard homepage with search (auth required)
- `/stocks/[id]` → Stock detail (auth required)
- `/backtests` → Backtests (auth required)
- `/login`, `/register` → Auth pages (public)

### Auth Flow Changes

| Component | Before | After |
|-----------|--------|-------|
| `AuthGuard` redirect | → `/login` | → `/` (Landing Page) |
| Login success (`login/page.tsx`) | `router.push("/")` | `router.push("/home")` |
| Register success (`register/page.tsx`) | `router.push("/login")` | No change needed (already correct) |
| Logout (`Header.tsx`) | `router.push("/login")` | No change needed (keep going to `/login`) |
| `Sidebar` home link | `/` | `/home` |
| `Header` logo link | `/` | `/home` |

### Authenticated user visiting `/`

The Landing Page (`/app/page.tsx`) is a Server Component and does not check auth state. If a logged-in user visits `/`, they see the Landing Page. This is acceptable — the Navbar will show "登入" and "免費開始" buttons, but clicking them will redirect to dashboard since they're already authenticated. No middleware or redirect logic needed.

## Visual Design

### Style
- Clean, modern, white-background with alternating light gray sections
- Font: Geist (existing, consistent with dashboard)
- Primary color: Shadcn/UI default (existing)
- Icons: Lucide (existing)
- Illustrations: CSS/SVG abstract charts (no external images)
- Dark mode: supported via next-themes (existing)

### SEO Metadata

The root `app/page.tsx` exports metadata:
```ts
export const metadata: Metadata = {
  title: "Stock Tracer — 台股追蹤分析平台",
  description: "即時台股行情追蹤、籌碼分析、智能回測系統，免費開源的一站式投資分析工具。",
};
```

### Page Sections (top to bottom)

#### 1. Navbar (sticky top)
- Left: Logo icon (TrendingUp) + "Stock Tracer"
- Center: anchor links — 功能、優勢、FAQ (scroll to section, with `prefers-reduced-motion` handling)
- Right: 登入 (ghost button → /login), 免費開始 (primary button → /register)
- Mobile: hamburger menu

#### 2. Hero
- Left side: headline + subtitle + 2 CTA buttons
  - H1: "掌握台股投資先機"
  - Subtitle: "即時行情追蹤、深度籌碼分析、智能回測系統，一站式台股投資分析平台。"
  - CTA: "免費開始使用" (primary), "了解更多" (outline, scrolls to features)
- Right side: abstract SVG illustration (dashboard mockup with chart lines)
- Layout: side-by-side on desktop, stacked on mobile

#### 3. Features (id="features")
- Section title: "核心功能"
- 4-column grid (2x2 on mobile):
  1. 即時行情追蹤 — icon: BarChart3 — "上市上櫃股票 K 線圖、成交量、漲跌幅一目瞭然"
  2. 深度籌碼分析 — icon: PieChart — "三大法人買賣超、大戶持股、融資融券、分點券商完整呈現"
  3. 智能回測系統 — icon: LineChart — "多種內建策略、自訂參數，歷史數據驗證投資想法"
  4. 到價提醒 & 自選 — icon: Bell — "設定價格條件，即時通知不漏接"

#### 4. How it Works (id="how-it-works")
- Section title: "三步驟開始"
- 3 steps with numbered circles:
  1. 註冊帳號 — "30 秒完成註冊，免費使用"
  2. 搜尋股票 — "輸入代號或名稱，即時查看行情"
  3. 開始分析 — "籌碼、回測、提醒，全方位掌握"

#### 5. Why Stock Tracer (id="advantages")
- Section title: "為什麼選擇 Stock Tracer"
- 3-4 cards in a row:
  - 每日自動更新 — "排程爬蟲自動抓取最新資料，不需手動操作"
  - 全市場覆蓋 — "涵蓋上市（TWSE）及上櫃（TPEX）全部股票"
  - 資料來源可靠 — "TWSE、TPEX、TDCC 官方公開資料"
  - 開源透明 — "完整原始碼公開，歡迎貢獻"

#### 6. FAQ (id="faq")
- Section title: "常見問題"
- Accordion (Shadcn/UI) with 4 items:
  - Q: Stock Tracer 是免費的嗎？ A: 是的，目前所有功能完全免費。
  - Q: 資料多久更新一次？ A: 每個交易日收盤後自動更新（約 14:00-18:00）。
  - Q: 支援哪些股票？ A: 涵蓋台灣上市（TWSE）及上櫃（TPEX）所有股票。
  - Q: 回測系統支援哪些策略？ A: 內建均線、法人、大戶持股、融資融券四種策略，可自訂參數。

#### 7. Footer CTA + Footer
- CTA section: "準備好開始了嗎？" + primary button
- Footer: "© 2026 Stock Tracer" + GitHub link

## Components

### New files
| File | Type | Responsibility |
|------|------|----------------|
| `app/page.tsx` | Server Component | Landing Page (assembles sections, exports metadata) |
| `components/landing/Navbar.tsx` | Client Component | Sticky nav with mobile menu + smooth scroll |
| `components/landing/Hero.tsx` | Server Component | Hero section with SVG illustration |
| `components/landing/Features.tsx` | Server Component | 4 feature cards |
| `components/landing/HowItWorks.tsx` | Server Component | 3-step flow |
| `components/landing/Advantages.tsx` | Server Component | Why choose us cards |
| `components/landing/FAQ.tsx` | Client Component | Accordion FAQ |
| `components/landing/Footer.tsx` | Server Component | Footer with CTA |
| `components/landing/HeroIllustration.tsx` | Server Component | Abstract SVG chart illustration |

### Modified files
| File | Change |
|------|--------|
| `app/(dashboard)/page.tsx` | Move to `app/(dashboard)/home/page.tsx` |
| `components/AuthGuard.tsx` | Redirect: `/login` → `/` |
| `components/Sidebar.tsx` | Home link href: `/` → `/home`; update `isActive` special case for `/home` |
| `components/Header.tsx` | Logo link: `/` → `/home`; update `getPageTitle`: map `"/home"` → `"市場總覽"` (was `"/"`) |
| `app/login/page.tsx` | Login success redirect: `router.push("/")` → `router.push("/home")` |

### Deleted files
| File | Reason |
|------|--------|
| `app/welcome/page.tsx` | Replaced by root Landing Page |
| `app/welcome/layout.tsx` | No longer needed |

### New dependency
- Shadcn/UI Accordion — `npx shadcn add accordion` for FAQ section

## Testing

- Landing Page renders at `/` without authentication
- Authenticated user visiting `/` sees Landing Page (no redirect)
- All anchor links scroll to correct sections (with `prefers-reduced-motion` handling)
- "登入" button navigates to `/login`
- "免費開始" button navigates to `/register`
- Login redirects to `/home` (dashboard)
- Unauthenticated access to `/home`, `/stocks/*`, `/backtests/*` redirects to `/`
- Logout redirects to `/login`
- `/home` renders dashboard search page with correct page title "市場總覽"
- Sidebar home link points to `/home` and highlights correctly
- Mobile responsive: hamburger menu works, sections stack correctly
- Dark mode works on Landing Page
- SEO metadata (title, description) renders correctly
