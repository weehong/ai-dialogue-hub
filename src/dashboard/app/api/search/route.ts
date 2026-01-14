import { NextRequest, NextResponse } from 'next/server';
import { searchMessages } from '@/lib/meilisearch';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q') || '';
    const chatId = searchParams.get('chatId');
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    if (!query.trim()) {
      return NextResponse.json({
        hits: [],
        query: '',
        processingTimeMs: 0,
        estimatedTotalHits: 0,
      });
    }

    const results = await searchMessages(
      query,
      chatId ? parseInt(chatId, 10) : undefined,
      limit,
      offset
    );

    return NextResponse.json(results);
  } catch (error) {
    console.error('Search failed:', error);
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}
