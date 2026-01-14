import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/mongodb';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const chatId = searchParams.get('chatId');
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const sortField = searchParams.get('sortField') || 'date';
    const sortOrder = searchParams.get('sortOrder') === 'asc' ? 1 : -1;

    if (!chatId) {
      return NextResponse.json(
        { error: 'chatId is required' },
        { status: 400 }
      );
    }

    const db = await getDb();
    const skip = (page - 1) * limit;

    // Get messages for the specific chat
    const messages = await db
      .collection('messages')
      .find({ chat_id: parseInt(chatId, 10) })
      .sort({ [sortField]: sortOrder })
      .skip(skip)
      .limit(limit)
      .toArray();

    // Get total count for pagination
    const total = await db
      .collection('messages')
      .countDocuments({ chat_id: parseInt(chatId, 10) });

    // Transform _id to string
    const transformedMessages = messages.map((msg) => ({
      ...msg,
      _id: msg._id.toString(),
    }));

    return NextResponse.json({
      messages: transformedMessages,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error('Failed to fetch messages:', error);
    return NextResponse.json(
      { error: 'Failed to fetch messages' },
      { status: 500 }
    );
  }
}
