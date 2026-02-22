import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Textarea } from "../../components/Textarea";
import { Input } from "../../components/Input";
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

const initials = (name: string) =>
  name
    .split(" ")
    .map((chunk) => chunk[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

export const CandidateChat = () => {
  const { auth } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = () => {
    apiFetch<{ items: Conversation[] }>("/api/candidate/chat/conversations")
      .then((data) => {
        setConversations(data.items);
        if (!activeConversation && data.items.length) {
          setActiveConversation(data.items[0]);
        }
      })
      .catch((err) => setError((err as Error).message));
  };

  const loadMessages = (conversationId: number) => {
    apiFetch<{ items: Message[] }>(`/api/candidate/chat/conversations/${conversationId}/messages`)
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
      await apiFetch(`/api/candidate/chat/conversations/${activeConversation.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: message }),
      });
      setMessage("");
      setIsTyping(true);
      setTimeout(() => setIsTyping(false), 800);
      loadMessages(activeConversation.id);
      loadConversations();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const filteredConversations = useMemo(() => {
    if (!search) return conversations;
    const lower = search.toLowerCase();
    return conversations.filter(
      (item) =>
        item.other_user.full_name.toLowerCase().includes(lower) ||
        (item.job?.title || "").toLowerCase().includes(lower)
    );
  }, [conversations, search]);

  return (
    <div className="space-y-6">
      <PageHeader kicker="Candidate Suite" title="Messages" subtitle="Chat with HR teams just like LinkedIn or WhatsApp." />
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card variant="glass" className="space-y-4">
          <div className="text-lg font-semibold text-white">Conversations</div>
          <Input
            label="Search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {filteredConversations.length === 0 && (
            <EmptyState title="No conversations" description="Apply to a job to open a conversation." />
          )}
          <div className="space-y-2">
            {filteredConversations.map((conversation) => (
              <button
                key={conversation.id}
                className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                  activeConversation?.id === conversation.id ? "border-accent bg-panelMuted/70" : "border-border"
                }`}
                onClick={() => setActiveConversation(conversation)}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white">
                    {initials(conversation.other_user.full_name)}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-white">{conversation.other_user.full_name}</div>
                    <div className="text-xs text-textMuted">
                      {conversation.job?.title || "General"} - {conversation.last_message?.content ?? "No messages"}
                    </div>
                  </div>
                  {conversation.unread_count > 0 && (
                    <div className="rounded-full bg-accent px-2 py-0.5 text-[10px] text-white">
                      {conversation.unread_count}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card variant="glass" className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-white">
                {activeConversation ? activeConversation.other_user.full_name : "Select a conversation"}
              </div>
              <div className="text-xs text-textMuted">
                {activeConversation?.job?.title || "General discussion"}
              </div>
            </div>
            {isTyping && <span className="text-xs text-textMuted">Typing...</span>}
          </div>
          {error && <p className="text-danger">{error}</p>}
          <div className="flex-1 overflow-auto rounded-md border border-border bg-panelMuted/70 p-4 text-sm">
            {messages.length === 0 && <div className="text-textMuted">No messages yet.</div>}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`mb-3 flex flex-col ${
                  msg.sender_user_id === auth.user?.id ? "items-end" : "items-start"
                }`}
              >
                <div className="text-xs text-textMuted">{new Date(msg.created_at).toLocaleTimeString()}</div>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                    msg.sender_user_id === auth.user?.id
                      ? "bg-accent text-white"
                      : "bg-panel text-text"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Textarea
              label="Message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <div className="flex justify-end">
              <Button onClick={sendMessage} disabled={!activeConversation}>
                Send
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
