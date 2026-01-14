import { MongoClient } from 'mongodb';
import { MeiliSearch } from 'meilisearch';

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const MONGODB_DATABASE = process.env.MONGODB_DATABASE || 'telegram_logs';
const MEILISEARCH_HOST = process.env.MEILISEARCH_HOST || 'http://localhost:7700';
const MEILISEARCH_API_KEY = process.env.MEILISEARCH_API_KEY || '';
const BATCH_SIZE = parseInt(process.env.SYNC_BATCH_SIZE || '1000', 10);

const meiliClient = new MeiliSearch({
  host: MEILISEARCH_HOST,
  apiKey: MEILISEARCH_API_KEY,
});

const MESSAGES_INDEX = 'messages';

async function syncMessages() {
  console.log('Starting Meilisearch sync...');
  console.log(`MongoDB: ${MONGODB_URI}`);
  console.log(`Meilisearch: ${MEILISEARCH_HOST}`);

  // Connect to MongoDB
  const mongoClient = new MongoClient(MONGODB_URI);
  await mongoClient.connect();
  console.log('Connected to MongoDB');

  const db = mongoClient.db(MONGODB_DATABASE);
  const messagesCollection = db.collection('messages');

  // Create or get the index
  const index = meiliClient.index(MESSAGES_INDEX);

  // Configure index settings
  console.log('Configuring Meilisearch index settings...');
  await index.updateSettings({
    searchableAttributes: [
      'text',
      'caption',
      'from_user.first_name',
      'from_user.last_name',
      'from_user.username',
    ],
    filterableAttributes: ['chat_id', 'from_user.id', 'date', 'was_edited'],
    sortableAttributes: ['date', 'logged_at', 'message_id'],
    displayedAttributes: [
      'id',
      '_id',
      'message_id',
      'chat_id',
      'date',
      'from_user',
      'text',
      'caption',
      'logged_at',
      'was_edited',
    ],
  });
  console.log('Index settings configured');

  // Get total count
  const totalCount = await messagesCollection.countDocuments();
  console.log(`Total messages to sync: ${totalCount}`);

  if (totalCount === 0) {
    console.log('No messages to sync');
    await mongoClient.close();
    return;
  }

  // Sync in batches
  let processed = 0;
  let skip = 0;

  while (skip < totalCount) {
    const messages = await messagesCollection
      .find({})
      .sort({ date: -1 })
      .skip(skip)
      .limit(BATCH_SIZE)
      .toArray();

    if (messages.length === 0) break;

    // Transform messages for Meilisearch
    const documents = messages.map((msg) => ({
      id: msg._id.toString(),
      _id: msg._id.toString(),
      message_id: msg.message_id,
      chat_id: msg.chat_id,
      date: msg.date instanceof Date ? msg.date.toISOString() : msg.date,
      from_user: msg.from_user,
      text: msg.text,
      caption: msg.caption,
      logged_at:
        msg.logged_at instanceof Date
          ? msg.logged_at.toISOString()
          : msg.logged_at,
      was_edited: msg.was_edited || false,
    }));

    // Add documents to Meilisearch
    const task = await index.addDocuments(documents, { primaryKey: 'id' });
    console.log(`Batch indexed. Task ID: ${task.taskUid}`);

    processed += messages.length;
    skip += BATCH_SIZE;
    console.log(`Progress: ${processed}/${totalCount} (${((processed / totalCount) * 100).toFixed(1)}%)`);
  }

  console.log('Sync completed successfully!');
  console.log(`Total messages indexed: ${processed}`);

  await mongoClient.close();
}

// Run continuous sync (watch for changes)
async function watchAndSync() {
  console.log('Starting continuous sync mode...');

  const mongoClient = new MongoClient(MONGODB_URI);
  await mongoClient.connect();
  console.log('Connected to MongoDB for change stream');

  const db = mongoClient.db(MONGODB_DATABASE);
  const messagesCollection = db.collection('messages');
  const index = meiliClient.index(MESSAGES_INDEX);

  // Watch for changes
  const changeStream = messagesCollection.watch([], {
    fullDocument: 'updateLookup',
  });

  changeStream.on('change', async (change) => {
    try {
      switch (change.operationType) {
        case 'insert':
        case 'update':
          if (change.fullDocument) {
            const doc = {
              id: change.fullDocument._id.toString(),
              _id: change.fullDocument._id.toString(),
              message_id: change.fullDocument.message_id,
              chat_id: change.fullDocument.chat_id,
              date:
                change.fullDocument.date instanceof Date
                  ? change.fullDocument.date.toISOString()
                  : change.fullDocument.date,
              from_user: change.fullDocument.from_user,
              text: change.fullDocument.text,
              caption: change.fullDocument.caption,
              logged_at:
                change.fullDocument.logged_at instanceof Date
                  ? change.fullDocument.logged_at.toISOString()
                  : change.fullDocument.logged_at,
              was_edited: change.fullDocument.was_edited || false,
            };
            await index.addDocuments([doc], { primaryKey: 'id' });
            console.log(`Indexed: ${change.operationType} - ${doc.id}`);
          }
          break;
        case 'delete':
          const deletedId = change.documentKey._id.toString();
          await index.deleteDocument(deletedId);
          console.log(`Deleted from index: ${deletedId}`);
          break;
      }
    } catch (error) {
      console.error('Failed to sync change:', error);
    }
  });

  changeStream.on('error', (error) => {
    console.error('Change stream error:', error);
  });

  console.log('Watching for changes...');

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down sync...');
    await changeStream.close();
    await mongoClient.close();
    process.exit(0);
  });
}

// Main entry point
const args = process.argv.slice(2);
const mode = args[0] || 'full';

if (mode === 'watch') {
  watchAndSync().catch(console.error);
} else {
  syncMessages()
    .then(() => {
      if (args.includes('--watch')) {
        return watchAndSync();
      }
      process.exit(0);
    })
    .catch((error) => {
      console.error('Sync failed:', error);
      process.exit(1);
    });
}
