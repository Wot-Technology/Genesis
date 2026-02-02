# WoT Landing Sites

Three interconnected landing pages for the Web of Thoughts project:

- **wot.rocks** — Consumer-friendly landing page (the "why")
- **wot.technology** — Technical documentation (the "how")
- **now.pub** — Identity namespace service (live status/presence)

## Structure

```
wot-sites/
├── shared/
│   └── design-system.css     # Shared CSS (fonts, colors, components)
├── wot-rocks/
│   └── index.html            # Main landing page
├── wot-technology/
│   └── index.html            # Technical spec landing
├── now-pub/
│   └── index.html            # Identity reservation
├── form-worker/
│   ├── Cargo.toml
│   ├── wrangler.toml
│   └── src/lib.rs            # Rust Cloudflare Worker
└── README.md
```

## Design System

Brand colors from existing assets:
- Primary gradient: `#FFCC00` → `#F7931E`
- Secondary: `#E8A60C`, `#FF9E0D`
- Accent blue: `#126EB3`

Fonts:
- Headers: Quicksand (Google Fonts)
- Body: Source Sans 3 (Google Fonts)
- Code: JetBrains Mono

## Deployment

### Static Sites (Cloudflare Pages)

Each site can be deployed as a separate Cloudflare Pages project:

```bash
# Deploy wot.rocks
cd wot-rocks
npx wrangler pages deploy . --project-name=wot-rocks

# Deploy wot.technology
cd wot-technology
npx wrangler pages deploy . --project-name=wot-technology

# Deploy now.pub
cd now-pub
npx wrangler pages deploy . --project-name=now-pub
```

Note: You'll need to update the `../shared/design-system.css` path to either:
1. Inline the CSS
2. Host it on a CDN
3. Copy it into each site folder

### Form Worker (Cloudflare Workers)

The Rust-based form handler stores submissions in Cloudflare KV:

```bash
cd form-worker

# Create KV namespace
wrangler kv:namespace create "WOT_SIGNUPS"
# Copy the ID to wrangler.toml

# Build and deploy
wrangler deploy
```

### Connecting Forms to Worker

Update the form handlers in each HTML file to POST to the worker:

```javascript
// Replace the placeholder with actual API call
const res = await fetch('https://wot-form-worker.YOUR_SUBDOMAIN.workers.dev/api/wot-rocks/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, name, use_case })
});
```

### Custom Domains

In Cloudflare dashboard:
1. Add custom domain to each Pages project
2. Configure DNS records
3. Set up Worker routes for `/api/*` paths

## Local Development

Serve any site locally:

```bash
cd wot-rocks
python -m http.server 8000
# or
npx serve .
```

Note: Cross-site navigation (domain pills) won't work locally since they point to production domains.

## Form Endpoints

The Rust Worker handles these endpoints:

| Endpoint | Site | Data Collected |
|----------|------|----------------|
| `POST /api/now-pub/signup` | now.pub | subdomain, email, pubkey |
| `POST /api/wot-rocks/signup` | wot.rocks | email, name, use_case |
| `POST /api/wot-technology/signup` | wot.technology | email, github_username, interest |

## Next Steps

1. [ ] Replace placeholder form handlers with actual API calls
2. [ ] Set up Cloudflare KV namespace
3. [ ] Deploy Worker and update CORS origins
4. [ ] Deploy static sites to Pages
5. [ ] Configure custom domains
6. [ ] Add analytics (Plausible or CF Web Analytics)
7. [ ] Add email notification on signup (via Worker + email service)
