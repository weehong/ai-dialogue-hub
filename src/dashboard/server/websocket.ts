import { WebSocketServer, WebSocket } from 'ws';
import { MongoClient, ChangeStream, ChangeStreamDocument, ObjectId, Document } from 'mongodb';

const WS_PORT = parseInt(process.env.WS_PORT || '8080', 10);
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const MONGODB_DATABASE = process.env.MONGODB_DATABASE || 'telegram_logs';

interface MessageDocument extends Document {
  _id: ObjectId;
  message_id: number;
  chat_id: number;
  date: Date;
  from_user?: {
    id: number;
    first_name?: string;
    last_name?: string;
    username?: string;
  };
  text?: string;
  caption?: string;
  logged_at: Date;
}

interface ActivatedChatDocument extends Document {
  _id: ObjectId;
  chat_id: number;
  chat_title?: string;
  chat_type?: string;
  activated_at: Date;
}

interface ClientInfo {
  ws: WebSocket;
  subscribedChats: Set<number>;
}

const clients: Set<ClientInfo> = new Set();

async function startServer() {
  // Connect to MongoDB
  const mongoClient = new MongoClient(MONGODB_URI);
  await mongoClient.connect();
  console.log('Connected to MongoDB');

  const db = mongoClient.db(MONGODB_DATABASE);
  const messagesCollection = db.collection<MessageDocument>('messages');
  const activatedChatsCollection = db.collection<ActivatedChatDocument>('activated_chats');

  // Create WebSocket server
  const wss = new WebSocketServer({ port: WS_PORT });
  console.log(`WebSocket server started on port ${WS_PORT}`);

  wss.on('connection', (ws) => {
    const clientInfo: ClientInfo = {
      ws,
      subscribedChats: new Set(),
    };
    clients.add(clientInfo);
    console.log('Client connected. Total clients:', clients.size);

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        if (message.type === 'subscribe' && message.chatId) {
          clientInfo.subscribedChats.add(message.chatId);
          console.log(`Client subscribed to chat ${message.chatId}`);
        } else if (message.type === 'unsubscribe' && message.chatId) {
          clientInfo.subscribedChats.delete(message.chatId);
          console.log(`Client unsubscribed from chat ${message.chatId}`);
        }
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    });

    ws.on('close', () => {
      clients.delete(clientInfo);
      console.log('Client disconnected. Total clients:', clients.size);
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      clients.delete(clientInfo);
    });
  });

  // Watch for changes in MongoDB
  const changeStream: ChangeStream<MessageDocument> = messagesCollection.watch([], {
    fullDocument: 'updateLookup',
  });

  changeStream.on('change', (change: ChangeStreamDocument<MessageDocument>) => {
    console.log('Change detected:', change.operationType);

    let messageType: string;
    let payload: Record<string, unknown>;

    switch (change.operationType) {
      case 'insert':
        messageType = 'new_message';
        payload = {
          ...change.fullDocument,
          _id: change.fullDocument?._id?.toString(),
        };
        break;
      case 'delete':
        messageType = 'delete_message';
        payload = {
          id: change.documentKey._id.toString(),
          chat_id: undefined, // Will be undefined for deletes without fullDocumentBeforeChange
        };
        break;
      case 'update':
        messageType = 'update_message';
        payload = {
          ...change.fullDocument,
          _id: change.fullDocument?._id?.toString(),
        };
        break;
      default:
        return;
    }

    const wsMessage = JSON.stringify({ type: messageType, payload });

    // Broadcast to all connected clients
    clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        // Send to clients subscribed to this chat or all clients if no subscription filter
        const chatId = (payload as { chat_id?: number }).chat_id;
        if (
          client.subscribedChats.size === 0 ||
          (chatId && client.subscribedChats.has(chatId))
        ) {
          client.ws.send(wsMessage);
        }
      }
    });
  });

  changeStream.on('error', (error) => {
    console.error('Change stream error:', error);
  });

  // Watch for new activated chats
  const activatedChatsChangeStream: ChangeStream<ActivatedChatDocument> = activatedChatsCollection.watch([], {
    fullDocument: 'updateLookup',
  });

  activatedChatsChangeStream.on('change', async (change: ChangeStreamDocument<ActivatedChatDocument>) => {
    console.log('Activated chat change detected:', change.operationType);

    if (change.operationType === 'insert' && change.fullDocument) {
      // Get message count for this group
      const messageCount = await messagesCollection.countDocuments({
        chat_id: change.fullDocument.chat_id,
      });

      const groupData = {
        _id: change.fullDocument._id.toString(),
        chat_id: change.fullDocument.chat_id,
        chat_title: change.fullDocument.chat_title,
        chat_type: change.fullDocument.chat_type,
        activated_at: change.fullDocument.activated_at,
        message_count: messageCount,
      };

      const wsMessage = JSON.stringify({
        type: 'new_group',
        payload: groupData,
      });

      // Broadcast to all connected clients (groups are global, not chat-specific)
      clients.forEach((client) => {
        if (client.ws.readyState === WebSocket.OPEN) {
          client.ws.send(wsMessage);
        }
      });
    }
  });

  activatedChatsChangeStream.on('error', (error) => {
    console.error('Activated chats change stream error:', error);
  });

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await changeStream.close();
    await activatedChatsChangeStream.close();
    await mongoClient.close();
    wss.close();
    process.exit(0);
  });
}

startServer().catch(console.error);
