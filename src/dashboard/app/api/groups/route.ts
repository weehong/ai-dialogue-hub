import { NextResponse } from 'next/server';
import { getDb } from '@/lib/mongodb';

export async function GET() {
  try {
    const db = await getDb();

    // Get all activated chats
    const groups = await db
      .collection('activated_chats')
      .find({})
      .sort({ activated_at: -1 })
      .toArray();

    // Get message counts for each group
    const groupsWithCounts = await Promise.all(
      groups.map(async (group) => {
        const messageCount = await db
          .collection('messages')
          .countDocuments({ chat_id: group.chat_id });

        return {
          ...group,
          _id: group._id.toString(),
          message_count: messageCount,
        };
      })
    );

    return NextResponse.json(groupsWithCounts);
  } catch (error) {
    console.error('Failed to fetch groups:', error);
    return NextResponse.json(
      { error: 'Failed to fetch groups' },
      { status: 500 }
    );
  }
}
