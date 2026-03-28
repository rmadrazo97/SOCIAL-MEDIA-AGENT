Add a new page to the frontend dashboard. The user will describe what the page should show.

Follow this workflow:

1. **Create page** — Add `frontend/src/app/dashboard/<name>/page.tsx`
   - Use `'use client'` directive
   - Import hooks from `@/lib/hooks` for data fetching
   - Import `api` from `@/lib/api` for mutations
   - Follow the existing page patterns (see `dashboard/page.tsx` for reference)

2. **Navigation** — Add a link in `frontend/src/components/layout/DashboardLayout.tsx`
   - Add to the sidebar nav items array
   - Use a Lucide React icon

3. **Backend** — If the page needs new data, create API endpoints first using the add-endpoint workflow:
   - Schema in `schemas/schemas.py`
   - Route in `api/*.py`
   - Method in `lib/api.ts`
   - Hook in `lib/hooks.ts`

Design conventions:
- Color palette: bg-ebony (dark), text-bone (light text), border-dun, bg-reseda (buttons), text-sage (accents)
- Use Tailwind CSS exclusively — no external UI libraries
- Icons: Lucide React (`lucide-react` package)
- Loading states: use skeleton divs with `animate-pulse`
- Empty states: centered text with suggestion
- Cards: `bg-ebony/50 border border-dun/20 rounded-lg p-4`
- Buttons: `bg-reseda hover:bg-reseda/80 text-bone px-4 py-2 rounded`

$ARGUMENTS
