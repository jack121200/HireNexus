import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Textarea } from "../../components/Textarea";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../../lib/auth";

type Conversation = {
  id: number;
  job?: { id: number; title: string } | null;
  other_user: { id: number; full_name: string; email: string };
  last_message?: { content: string } | null;
  unread_count: number;
};

type Message = {
  id: number;
  sender_user_id: number;
  content: string;
  created_at: string;
};

export const HrChat = () => {
  const { auth } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadConversations = () => {
    apiFetch<{ items: Conversation[] }>("/api/hr/chat/conversations")
      .then((data) => {
        setConversations(data.items);
        if (!activeConversation && data.items.length) {
          setActiveConversation(data.items[0]);
        }
      })
      .catch((err) => setError((err as Error).message));
  };

  const loadMessages = (conversationId: number) => {
    apiFetch<{ items: Message[] }>(`/api/hr/chat/conversations/${conversationId}/messages`)
      .then((data) => setMessages(data.items))
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (activeConversation) {
      loadMessages(activeConversation.id);
    }
  }, [activeConversation]);

  const sendMessage = async () => {
    if (!activeConversation || !message.trim()) return;
    try {
      await apiFetch(`/api/hr/chat/conversations/${activeConversation.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: message }),
      });
      setMessage("");
      loadMessages(activeConversation.id);
      loadConversations();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader kicker="HR Suite" title="Chat" subtitle="Coordinate with candidates in real time." />
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card variant="glass" className="space-y-4">
          <div className="text-lg font-semibold text-white">Conversations</div>
          {conversations.length === 0 && (
            <EmptyState title="No conversations" description="Start by posting jobs and receiving applicants." />
          )}
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                activeConversation?.id === conversation.id
                  ? "border-accent bg-panelMuted/70"
                  : "border-border"
              }`}
              onClick={() => setActiveConversation(conversation)}
            >
              <div className="font-semibold text-white">{conversation.other_user.full_name}</div>
              <div className="text-xs text-textMuted">
                {conversation.job?.title || "General"} - {conversation.last_message?.content ?? "No messages"}
              </div>
              {conversation.unread_count > 0 && (
                <div className="mt-1 text-xs text-accent">Unread: {conversation.unread_count}</div>
              )}
            </button>
          ))}
        </Card>

        <Card variant="glass" className="flex flex-col gap-4">
          <div className="text-lg font-semibold text-white">
            {activeConversation ? activeConversation.other_user.full_name : "Select a conversation"}
          </div>
          {error && <p className="text-danger">{error}</p>}
          <div className="flex-1 overflow-auto rounded-md border border-border bg-panelMuted/70 p-3 text-sm">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`mb-3 flex flex-col ${
                  msg.sender_user_id === auth.user?.id ? "items-end" : "items-start"
                }`}
              >
                <div className="text-xs text-textMuted">{new Date(msg.created_at).toLocaleTimeString()}</div>
                <div
                  className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                    msg.sender_user_id === auth.user?.id ? "bg-accent text-white" : "bg-panel text-text"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>
          <Textarea label="Message" value={message} onChange={(event) => setMessage(event.target.value)} />
          <Button onClick={sendMessage} disabled={!activeConversation}>
            Send
          </Button>
        </Card>
      </div>
    </div>
  );
};
