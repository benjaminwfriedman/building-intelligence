import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from chat_models import ChatMessage
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for chat history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        diagram_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        confidence REAL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_diagram_timestamp 
                    ON messages(diagram_id, timestamp)
                """)
                conn.commit()
                logger.info("Chat database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chat database: {e}")
            raise
    
    def save_message(self, message: ChatMessage) -> bool:
        """Save a chat message to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO messages (id, diagram_id, role, content, timestamp, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.diagram_id,
                    message.role,
                    message.content,
                    message.timestamp.isoformat(),
                    message.confidence
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    def get_chat_history(self, diagram_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get chat history for a diagram"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE diagram_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (diagram_id, limit))
                
                messages = []
                for row in cursor:
                    message = ChatMessage(
                        id=row['id'],
                        diagram_id=row['diagram_id'],
                        role=row['role'],
                        content=row['content'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        confidence=row['confidence']
                    )
                    messages.append(message)
                
                # Return in chronological order
                return list(reversed(messages))
                
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
    
    def clear_chat_history(self, diagram_id: str) -> bool:
        """Clear chat history for a diagram"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE diagram_id = ?", (diagram_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
            return False
    
    def create_message_id(self) -> str:
        """Generate a unique message ID"""
        return str(uuid.uuid4())

# Global chat service instance
chat_service = ChatService()