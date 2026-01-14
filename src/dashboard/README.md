# Telegram Botstack Dashboard

Web interface for browsing and searching Telegram messages logged by Logta bot.

## Features

- **Group Browser** - View all logged groups/chats
- **Message Viewer** - Browse messages with pagination
- **Full-text Search** - Search messages via Meilisearch
- **Real-time Updates** - WebSocket connection for live message streaming
- **Edit History** - View original content of edited messages

## Tech Stack

- [Next.js 14](https://nextjs.org) - React framework with App Router
- [shadcn/ui](https://ui.shadcn.com) - UI components
- [Tailwind CSS](https://tailwindcss.com) - Styling
- [MongoDB](https://mongodb.com) - Message storage
- [Meilisearch](https://meilisearch.com) - Full-text search

## Getting Started

### Prerequisites

- Node.js 18+
- MongoDB instance with logged messages
- Meilisearch instance (optional, for search)

### Environment Variables

Create `.env.local`:

```ini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=telegram_logs
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your_api_key
```

### Development

```bash
# install dependencies
npm install

# run development server
npm run dev

# run websocket server (separate terminal)
npx ts-node server/websocket.ts
```

Open [http://localhost:3000](http://localhost:3000).

### Production

```bash
# build
npm run build

# start
npm start
```

### Docker

From the repository root:

```bash
docker compose up -d dashboard
```

## Project Structure

```
dashboard/
├── app/
│   ├── api/           # api routes
│   │   ├── groups/
│   │   ├── messages/
│   │   └── search/
│   ├── groups/        # group detail pages
│   ├── layout.tsx
│   └── page.tsx       # home page
├── components/
│   ├── ui/            # shadcn components
│   ├── data-table.tsx
│   ├── groups-table.tsx
│   ├── messages-table.tsx
│   └── search-input.tsx
├── lib/
│   ├── mongodb.ts     # database connection
│   ├── meilisearch.ts # search client
│   └── types.ts       # typescript types
└── server/
    ├── websocket.ts   # ws server for real-time
    └── sync-meilisearch.ts  # search index sync
```

## API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/groups` | GET | List all logged groups |
| `/api/messages` | GET | Get messages (query: `chatId`, `page`, `limit`) |
| `/api/messages/[id]` | GET | Get single message by ID |
| `/api/search` | GET | Search messages (query: `q`, `chatId`) |
