# PRD-06: Frontend Dashboard & UI

## Domain
Next.js application — pages, components, layouts, API integration.

## Dependencies
- PRD-01 (project structure, Docker)
- PRD-02 (auth flow, login/register pages)

## Goal
A clean, fast dashboard where creators see their performance at a glance, read AI insights, and take action — all within 3 clicks.

---

## 1. Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Styling:** Tailwind CSS
- **State:** React Context + SWR (or TanStack Query) for server state
- **Charts:** Recharts or Chart.js
- **Icons:** Lucide React
- **Forms:** React Hook Form + Zod validation

## 2. Page Map

```
/                          → Redirect to /dashboard or /login
/login                     → Login page
/register                  → Registration page
/dashboard                 → Main dashboard (daily brief + overview)
/dashboard/accounts        → Manage connected accounts
/dashboard/posts           → Post list with metrics
/dashboard/posts/[id]      → Single post detail + diagnostic
/dashboard/recommendations → Active recommendations
/dashboard/remix/[postId]  → Remix generator for a post
/dashboard/settings        → User settings
```

## 3. Page Specifications

### Dashboard Home (`/dashboard`)

**Layout:** Two-column on desktop, single column on mobile.

**Left Column (main):**
- **Daily Brief Card** — Today's AI-generated brief
  - Greeting + headline
  - Expandable sections (yesterday, weekly trend, active posts)
  - Action items as checkboxes
- **Recent Posts Feed** — Last 5 posts with:
  - Thumbnail, caption preview, posted time
  - Key metrics (views, likes, comments)
  - Performance score badge (color-coded)
  - Click → post detail

**Right Column (sidebar):**
- **Account Summary Card**
  - Platform icon + username
  - Follower count
  - 7-day views total
  - Trend arrow (up/down/stable)
- **Top Recommendations** (top 3)
  - Title + type badge
  - Accept / Dismiss buttons
- **Quick Actions**
  - "Generate Remix" button
  - "Sync Now" button

### Post List (`/dashboard/posts`)

- Filterable by: platform, post type, date range, performance label
- Sortable by: date, views, engagement, performance score
- Table/grid toggle
- Each row shows: thumbnail, caption (truncated), platform, type, date, views, engagement, score

### Post Detail (`/dashboard/posts/[id]`)

**Header:**
- Post embed/preview (thumbnail + caption)
- Platform badge + post type badge
- Posted date + permalink

**Metrics Section:**
- Current metrics (views, likes, comments, shares, saves)
- Performance score (large, color-coded)
- "vs baseline" comparison for each metric
- Metrics over time chart (line chart showing snapshots)

**AI Diagnostic Section:**
- Summary paragraph
- Key factors (card per factor with impact badge)
- "What to repeat" list
- "What to improve" list
- "Regenerate Diagnostic" button

**Actions:**
- "Generate Remix" → navigates to remix page
- "View Similar Posts" (future)

### Recommendations (`/dashboard/recommendations`)

- List of recommendation cards
- Each card: type badge, title, full content, priority indicator
- Actions: Accept (moves to "accepted" tab), Dismiss
- Tabs: Active | Accepted | Dismissed
- Filter by type

### Remix Generator (`/dashboard/remix/[postId]`)

- Shows original post summary
- Format selector: Carousel, Reel Script, Story Series
- "Generate" button
- Results displayed as cards:
  - Carousel: slide-by-slide preview
  - Reel: script view with hook + caption
- "Copy to Clipboard" for each variation

### Account Management (`/dashboard/accounts`)

- List of connected accounts with status
- "Connect Instagram" / "Connect TikTok" buttons
- Per account: username, platform, status badge, last synced
- Actions: Sync Now, Disconnect
- Status indicators: Active (green), Expired (yellow), Revoked (red)

### Settings (`/dashboard/settings`)

- Profile: name, email, password change
- Notification preferences (future)
- Delete account (with confirmation modal)

## 4. Component Library

### Core Components
```
components/
├── ui/
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Modal.tsx
│   ├── Input.tsx
│   ├── Select.tsx
│   ├── Tabs.tsx
│   ├── Skeleton.tsx        # Loading states
│   └── EmptyState.tsx
├── layout/
│   ├── DashboardLayout.tsx  # Sidebar + header + content
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   └── MobileNav.tsx
├── charts/
│   ├── MetricsLineChart.tsx
│   ├── PerformanceBar.tsx
│   └── TrendArrow.tsx
├── posts/
│   ├── PostCard.tsx
│   ├── PostTable.tsx
│   ├── PostMetricsBadge.tsx
│   └── PerformanceScore.tsx
├── insights/
│   ├── DailyBriefCard.tsx
│   ├── DiagnosticPanel.tsx
│   ├── RecommendationCard.tsx
│   └── RemixResult.tsx
└── accounts/
    ├── AccountCard.tsx
    ├── ConnectButton.tsx
    └── AccountStatusBadge.tsx
```

## 5. API Client Layer

```typescript
// lib/api.ts
class ApiClient {
  // Auth
  login(email: string, password: string): Promise<TokenResponse>
  register(email: string, password: string, name: string): Promise<User>
  getMe(): Promise<User>

  // Accounts
  getAccounts(): Promise<Account[]>
  connectInstagram(): Promise<{ redirect_url: string }>
  connectTikTok(): Promise<{ redirect_url: string }>
  disconnectAccount(id: string): Promise<void>
  syncAccount(id: string): Promise<void>

  // Posts
  getPosts(accountId: string, filters?: PostFilters): Promise<PaginatedPosts>
  getPost(id: string): Promise<PostDetail>
  getPostMetrics(id: string): Promise<PostMetric[]>

  // Insights
  getDailyBrief(accountId: string): Promise<DailyBrief>
  getBriefHistory(accountId: string): Promise<DailyBrief[]>
  getPostDiagnostic(postId: string): Promise<Diagnostic>
  regenerateDiagnostic(postId: string): Promise<Diagnostic>

  // Recommendations
  getRecommendations(accountId: string): Promise<Recommendation[]>
  updateRecommendation(id: string, status: string): Promise<void>

  // Remix
  generateRemix(postId: string, format: string): Promise<Remix[]>

  // Metrics
  getAccountMetrics(accountId: string, period: string): Promise<AccountMetrics>
}
```

## 6. Design Principles

- **Dark mode first** (creators often work late)
- **Mobile responsive** (creators check on phone)
- **Fast loading** — skeleton loaders, no spinners
- **Scannable** — use color, badges, and hierarchy to surface key info
- **Actionable** — every screen should have a clear next action

### Color System
- Performance colors: Red (underperforming) → Yellow (average) → Green (above avg) → Purple (viral)
- Platform colors: Instagram gradient, TikTok black/cyan
- Neutral: Slate/zinc palette

## 7. Loading & Error States

Every data-fetching component must handle:
1. **Loading:** Skeleton placeholder matching the content shape
2. **Error:** Inline error message with "Retry" button
3. **Empty:** Helpful empty state with call-to-action (e.g., "Connect an account to get started")

## 8. Acceptance Criteria

- [ ] Login and registration pages functional
- [ ] Dashboard loads with daily brief and recent posts
- [ ] Post list page with filtering and sorting
- [ ] Post detail page shows metrics + AI diagnostic
- [ ] Recommendations page with accept/dismiss actions
- [ ] Remix generator produces and displays variations
- [ ] Account management with connect/disconnect flow
- [ ] Responsive layout (desktop + mobile)
- [ ] Loading skeletons on all data-dependent components
- [ ] Error states with retry on all API calls
- [ ] All pages accessible within 2 clicks from dashboard

## 9. Out of Scope (MVP)
- Dark/light mode toggle (ship dark mode only)
- Notification system
- Onboarding wizard / product tour
- PWA / offline support
- Internationalization
