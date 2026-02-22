//file name is InterviewSession.tsx

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "./Button";
import { Card } from "./Card";
import { TalkingHeadAvatar, type TalkingHeadHandle } from "./TalkingHeadAvatar";
import { apiFetch } from "../lib/api";
import { getAuthToken, useAuth } from "../lib/auth";

type Question = {
  id: string;
  question: string;
  difficulty: string;
  category: string;
  rubric_points: string[];
};

type SpeechRecognition = {
  start: () => void;
  stop: () => void;
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: (event: any) => void;
  onend: () => void;
  onerror?: (event: any) => void;
};

type InterviewResponse = {
  interview: {
    id: number;
    status: string;
    overall_score: number | null;
    confidence_score: number | null;
    report: any;
  };
};

type ChatMessage = {
  id: string;
  role: "ai" | "candidate";
  content: string;
  timestamp: string;
};

type NextQuestionResponse = {
  question?: Question;
  done: boolean;
  asked_count: number;
  total_count: number;
};

type ListeningTarget = "primary" | "followup" | "greeting" | null;

type Phase = "idle" | "intro" | "asking" | "listening" | "thinking" | "followup" | "completed";

const formatTime = (seconds: number) => {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${rest}s`;
};

const buildTranscript = (messages: ChatMessage[]) =>
  messages.map((msg) => `${msg.role === "ai" ? "AI" : "Candidate"}: ${msg.content}`).join("\n");

export const InterviewSession = ({ interviewId }: { interviewId: number }) => {
  const { auth } = useAuth();
  const sttProvider = import.meta.env.VITE_STT_PROVIDER || "browser";
  const useStreamingStt = sttProvider === "assemblyai";
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const avatarRef = useRef<TalkingHeadHandle | null>(null);
  const speakQueue = useRef(Promise.resolve());
  const [status, setStatus] = useState<"idle" | "running" | "completed">("idle");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<InterviewResponse["interview"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(useStreamingStt);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [followupText, setFollowupText] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [hasBegun, setHasBegun] = useState(false);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [sttStatus, setSttStatus] = useState<"idle" | "connecting" | "listening" | "error">("idle");
  const [micMuted, setMicMuted] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(true);
  const [micLevel, setMicLevel] = useState(0);
  const [captionsOn, setCaptionsOn] = useState(true);
  const [liveTranscript, setLiveTranscript] = useState("");

  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [askedCount, setAskedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(8);
  const [answers, setAnswers] = useState<string[]>([]);

  const navigate = useNavigate();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const startedRef = useRef(false);
  const listeningTargetRef = useRef<ListeningTarget>(null);
  const listeningWindowRef = useRef(false);
  const recognitionActiveRef = useRef(false);
  const noSpeechTimerRef = useRef<number | null>(null);
  const lastVoiceAtRef = useRef(0);
  const listeningStartedAtRef = useRef(0);
  const lastAiSpokeAtRef = useRef(0);
  const finalizingRef = useRef(false);
  const messagesRef = useRef<ChatMessage[]>([]);
  const micMutedRef = useRef(micMuted);
  const hasBegunRef = useRef(hasBegun);
  const currentAnswerRef = useRef("");
  const currentFollowupRef = useRef("");
  const micLevelRef = useRef(0);
  const endedRef = useRef(false);
  const sessionFinalRef = useRef("");
  const sessionInterimRef = useRef("");
  const lastFinalChunkRef = useRef("");
  const pendingRecognitionStartRef = useRef(false);
  const repeatCountRef = useRef(0);
  const sttSocketRef = useRef<WebSocket | null>(null);
  const sttContextRef = useRef<AudioContext | null>(null);
  const sttWorkletRef = useRef<AudioWorkletNode | null>(null);
  const sttSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const sttGainRef = useRef<GainNode | null>(null);

  const lastMessage = useMemo(() => messages[messages.length - 1], [messages]);

  const enqueueSpeak = (text: string) =>
    new Promise<void>((resolve) => {
      speakQueue.current = speakQueue.current.then(async () => {
        if (!text.trim()) {
          resolve();
          return;
        }
        
        // Stop listening before speaking
        listeningWindowRef.current = false;
        if (noSpeechTimerRef.current) {
          window.clearTimeout(noSpeechTimerRef.current);
          noSpeechTimerRef.current = null;
        }
        setIsRecording(false);
        setIsAiSpeaking(true);
        
        try {
          await avatarRef.current?.enableAudio();
          await avatarRef.current?.speak(text);
        } catch (err) {
          console.error("Speech failed:", err);
          // Fallback to browser speech synthesis
          if ("speechSynthesis" in window) {
            await new Promise<void>((done) => {
              window.speechSynthesis.cancel();
              const utterance = new SpeechSynthesisUtterance(text);
              utterance.rate = 0.98;
              utterance.pitch = 1.02;
              utterance.onend = () => done();
              utterance.onerror = () => done();
              window.speechSynthesis.speak(utterance);
            });
          }
        }
        
        setIsAiSpeaking(false);
        lastAiSpokeAtRef.current = Date.now();
        resolve();
      });
    });

  const addMessage = (role: "ai" | "candidate", content: string) => {
    if (!content || !content.trim()) {
      console.warn("Attempting to add empty message");
      return;
    }
    
    setMessages((prev) => {
      const next = [
        ...prev,
        { id: `${role}-${Date.now()}-${Math.random()}`, role, content, timestamp: new Date().toISOString() },
      ];
      messagesRef.current = next;
      return next;
    });
  };

  const scheduleNoSpeechPrompt = () => {
    if (noSpeechTimerRef.current) {
      window.clearTimeout(noSpeechTimerRef.current);
    }
    noSpeechTimerRef.current = window.setTimeout(() => {
      if (!listeningWindowRef.current) return;
      
      if (listeningTargetRef.current === "greeting") {
        closeListeningWindow();
        requestNextQuestion();
        return;
      }
      
      const currentAnswer =
        listeningTargetRef.current === "followup" ? currentFollowupRef.current : currentAnswerRef.current;
      
      if (currentAnswer.trim()) return;
      
      if (repeatCountRef.current >= 2) {
        // Give up after 2 retries
        console.warn("No speech detected after 2 prompts, moving on");
        closeListeningWindow();
        if (listeningTargetRef.current === "primary") {
          handleAnswerSend("No answer provided", false);
        }
        return;
      }
      
      repeatCountRef.current += 1;
      promptRepeat();
    }, 20000);
  };

  const openListeningWindow = (target: ListeningTarget) => {
    console.log("Opening listening window for:", target);
    listeningTargetRef.current = target;
    listeningWindowRef.current = true;
    setIsRecording(true);
    setPhase("listening");
    setSpeechError(null);
    
    // Reset answer buffers
    currentAnswerRef.current = "";
    currentFollowupRef.current = "";
    sessionFinalRef.current = "";
    sessionInterimRef.current = "";
    lastFinalChunkRef.current = "";
    lastVoiceAtRef.current = Date.now();
    listeningStartedAtRef.current = Date.now();
    setLiveTranscript("");
    
    if (useStreamingStt) {
      startStreamingStt();
    } else {
      startRecognition();
    }
    
    scheduleNoSpeechPrompt();
  };

  const closeListeningWindow = () => {
    console.log("Closing listening window");
    listeningWindowRef.current = false;
    setIsRecording(false);
    stopRecognition();
    
    if (noSpeechTimerRef.current) {
      window.clearTimeout(noSpeechTimerRef.current);
      noSpeechTimerRef.current = null;
    }
  };

  const promptRepeat = async () => {
    closeListeningWindow();
    const prompt = "I did not catch that. Could you please repeat your answer?";
    addMessage("ai", prompt);
    await enqueueSpeak(prompt);
    openListeningWindow(listeningTargetRef.current ?? "primary");
  };

  const startRecognition = () => {
    if (!recognition || recognitionActiveRef.current) {
      pendingRecognitionStartRef.current = true;
      return;
    }
    
    try {
      recognition.start();
      recognitionActiveRef.current = true;
      pendingRecognitionStartRef.current = false;
      console.log("Speech recognition started");
    } catch (err) {
      console.error("Failed to start recognition:", err);
      pendingRecognitionStartRef.current = true;
    }
  };

  const stopRecognition = () => {
    if (!recognition || !recognitionActiveRef.current) return;
    
    try {
      recognition.stop();
      console.log("Speech recognition stopped");
    } catch (err) {
      console.error("Failed to stop recognition:", err);
    }
    recognitionActiveRef.current = false;
  };

  const cleanupStreamingStt = () => {
    console.log("Cleaning up streaming STT");
    
    if (sttWorkletRef.current) {
      sttWorkletRef.current.disconnect();
      sttWorkletRef.current.port.onmessage = null;
      sttWorkletRef.current = null;
    }
    if (sttSourceRef.current) {
      sttSourceRef.current.disconnect();
      sttSourceRef.current = null;
    }
    if (sttGainRef.current) {
      sttGainRef.current.disconnect();
      sttGainRef.current = null;
    }
    if (sttContextRef.current) {
      sttContextRef.current.close().catch(() => undefined);
      sttContextRef.current = null;
    }
    if (sttSocketRef.current) {
      try {
        sttSocketRef.current.close();
      } catch (err) {
        console.error("Failed to close STT socket:", err);
      }
      sttSocketRef.current = null;
    }
    setSttStatus("idle");
  };

  const applySttTranscript = (text: string, isFinal: boolean) => {
    if (!listeningWindowRef.current || micMutedRef.current) return;
    
    const cleaned = text.trim();
    if (!cleaned) return;
    
    lastVoiceAtRef.current = Date.now();
    scheduleNoSpeechPrompt();

    if (isFinal) {
      const normalized = cleaned.toLowerCase();
      // Prevent duplicate final transcripts
      if (normalized === lastFinalChunkRef.current) {
        console.log("Duplicate final transcript, skipping");
        return;
      }
      sessionFinalRef.current = `${sessionFinalRef.current} ${cleaned}`.trim();
      lastFinalChunkRef.current = normalized;
      sessionInterimRef.current = "";
      console.log("Final transcript chunk:", cleaned);
    } else {
      sessionInterimRef.current = cleaned;
      console.log("Interim transcript:", cleaned);
    }

    const combined = `${sessionFinalRef.current} ${sessionInterimRef.current}`.trim();
    
    if (listeningTargetRef.current === "followup") {
      currentFollowupRef.current = combined;
    } else {
      currentAnswerRef.current = combined;
    }
    
    setLiveTranscript(combined);
  };

  const downsampleBuffer = (buffer: Float32Array, inputRate: number, outputRate: number) => {
    if (outputRate === inputRate) return buffer;
    
    const rate = inputRate / outputRate;
    const newLength = Math.round(buffer.length / rate);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * rate);
      let sum = 0;
      let count = 0;
      
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
        sum += buffer[i];
        count += 1;
      }
      
      result[offsetResult] = count ? sum / count : 0;
      offsetResult += 1;
      offsetBuffer = nextOffsetBuffer;
    }
    
    return result;
  };

  const floatTo16BitPCM = (input: Float32Array) => {
    const buffer = new ArrayBuffer(input.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
    
    return buffer;
  };

  const startStreamingStt = async () => {
    if (!useStreamingStt || sttSocketRef.current) {
      console.log("STT already connected or not using streaming");
      return;
    }

    const token = getAuthToken();
    if (!token) {
      setSpeechError("Session expired. Please sign in again.");
      return;
    }

    const stream = mediaStream ?? (await requestMedia());
    if (!stream) return;

    const wsBase = (import.meta.env.VITE_WS_BASE_URL || baseUrl).replace(/^http/, "ws").replace(/\/$/, "");
    const wsUrl = `${wsBase}/ws/stt?token=${encodeURIComponent(token)}`;
    console.log("Connecting to STT WebSocket:", wsUrl);
    
    const socket = new WebSocket(wsUrl);
    socket.binaryType = "arraybuffer";
    sttSocketRef.current = socket;
    setSttStatus("connecting");

    socket.onopen = () => {
      console.log("STT WebSocket connected");
      setSttStatus("listening");
      
      const setupAudio = async () => {
        try {
          const audioContext = sttContextRef.current ?? new AudioContext();
          sttContextRef.current = audioContext;
          
          await audioContext.audioWorklet.addModule("/pcm-worklet.js");
          await audioContext.resume();
          
          const source = audioContext.createMediaStreamSource(stream);
          sttSourceRef.current = source;
          
          const worklet = new AudioWorkletNode(audioContext, "pcm-processor");
          sttWorkletRef.current = worklet;
          
          const gain = audioContext.createGain();
          gain.gain.value = 0; // Silent monitoring
          sttGainRef.current = gain;

          worklet.port.onmessage = (event) => {
            if (!listeningWindowRef.current || micMutedRef.current) return;
            if (socket.readyState !== WebSocket.OPEN) return;
            
            const input = event.data as Float32Array;
            const downsampled = downsampleBuffer(input, audioContext.sampleRate, 16000);
            const pcm = floatTo16BitPCM(downsampled);
            socket.send(pcm);
          };

          source.connect(worklet).connect(gain).connect(audioContext.destination);
          console.log("Audio worklet setup complete");
        } catch (err) {
          console.error("AudioWorklet setup failed:", err);
          setSpeechError("Audio processing failed. Live transcription unavailable.");
          setSttStatus("error");
          cleanupStreamingStt();
        }
      };

      setupAudio();
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.event === "stt.partial") {
          applySttTranscript(String(data.text || ""), false);
        } else if (data.event === "stt.final") {
          applySttTranscript(String(data.text || ""), true);
        } else if (data.event === "stt.error") {
          console.error("STT error:", data.message);
          setSpeechError(String(data.message || "Live transcription error."));
          setSttStatus("error");
        } else if (data.event === "stt.ready") {
          console.log("STT ready");
        }
      } catch (err) {
        console.error("Failed to parse STT message:", err);
      }
    };

    socket.onerror = (err) => {
      console.error("STT WebSocket error:", err);
      setSpeechError("Live transcription connection failed.");
      setSttStatus("error");
      cleanupStreamingStt();
    };

    socket.onclose = () => {
      console.log("STT WebSocket closed");
      cleanupStreamingStt();
    };
  };

  const requestNextQuestion = async (previousAnswer?: string, transcriptOverride?: string) => {
    try {
      setPhase("asking");
      setIsAiThinking(true);
      
      console.log("Requesting next question...");
      const response = await apiFetch<NextQuestionResponse>(`/api/candidate/interviews/${interviewId}/next-question`, {
        method: "POST",
        body: JSON.stringify({
          previous_question_id: currentQuestion?.id ?? null,
          previous_answer: previousAnswer ?? null,
          transcript: transcriptOverride ?? buildTranscript(messagesRef.current),
        }),
      });
      
      setIsAiThinking(false);
      setAskedCount(response.asked_count);
      setTotalCount(response.total_count || totalCount);
      
      if (response.done || !response.question) {
        console.log("Interview complete");
        setPhase("completed");
        closeListeningWindow();
        return;
      }
      
      const next = response.question;
      repeatCountRef.current = 0;
      setCurrentQuestion(next);
      setFollowupText(null);
      
      console.log("Next question:", next.question);
      addMessage("ai", next.question);
      await enqueueSpeak(next.question);
      
      if (!micMutedRef.current) {
        openListeningWindow("primary");
      }
    } catch (err) {
      console.error("Failed to get next question:", err);
      setError((err as Error).message);
      setIsAiThinking(false);
    }
  };

  const askFollowup = async (followup: string) => {
    setPhase("followup");
    setFollowupText(followup);
    
    console.log("Asking followup:", followup);
    addMessage("ai", followup);
    await enqueueSpeak(followup);
    
    if (!micMutedRef.current) {
      openListeningWindow("followup");
    }
  };

  const finalizeAnswer = async () => {
    if (finalizingRef.current) {
      console.log("Already finalizing answer");
      return;
    }
    
    const isFollowup = listeningTargetRef.current === "followup";
    const isGreeting = listeningTargetRef.current === "greeting";
    const answerText = (isFollowup ? currentFollowupRef.current : currentAnswerRef.current).trim();
    
    console.log("Finalizing answer:", { isFollowup, isGreeting, length: answerText.length });
    
    if (!answerText) {
      if (isGreeting) {
        closeListeningWindow();
        await requestNextQuestion();
        return;
      }
      promptRepeat();
      return;
    }
    
    finalizingRef.current = true;
    closeListeningWindow();
    
    try {
      if (isGreeting) {
        await handleGreeting(answerText);
      } else {
        await handleAnswerSend(answerText, isFollowup);
      }
    } finally {
      finalizingRef.current = false;
    }
  };

  const handleGreeting = async (answerText: string) => {
    console.log("Handling greeting:", answerText);
    
    const candidateMessage: ChatMessage = {
      id: `candidate-${Date.now()}-${Math.random()}`,
      role: "candidate",
      content: answerText,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => {
      const next = [...prev, candidateMessage];
      messagesRef.current = next;
      return next;
    });
    
    setIsAiThinking(true);
    setPhase("thinking");
    
    try {
      const transcriptNow = buildTranscript([...messagesRef.current]);
      const response = await apiFetch<{ reply?: string }>(
        `/api/candidate/interviews/${interviewId}/greeting-reply`,
        {
          method: "POST",
          body: JSON.stringify({
            transcript: transcriptNow,
          }),
        }
      );
      
      const replyText = response.reply?.trim() || "";
      if (replyText) {
        addMessage("ai", replyText);
        await enqueueSpeak(replyText);
      }
    } catch (err) {
      console.error("Greeting reply failed:", err);
      // Continue to first question anyway
    } finally {
      setIsAiThinking(false);
      await requestNextQuestion(answerText);
    }
  };

  const handleAnswerSend = async (answerText: string, isFollowup: boolean) => {
    if (!currentQuestion) {
      console.error("No current question!");
      return;
    }

    console.log("Sending answer:", { answerText, isFollowup, questionId: currentQuestion.id });

    const candidateMessage: ChatMessage = {
      id: `candidate-${Date.now()}-${Math.random()}`,
      role: "candidate",
      content: answerText,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => {
      const next = [...prev, candidateMessage];
      messagesRef.current = next;
      return next;
    });
    
    setIsAiThinking(true);
    setPhase("thinking");

    if (!isFollowup) {
      setAnswers((prev) => [...prev, answerText]);
    }

    try {
      const transcriptNow = buildTranscript([...messagesRef.current]);
      const response = await apiFetch<{ reply?: string; followup?: string; move_on?: boolean }>(
        `/api/candidate/interviews/${interviewId}/followup`,
        {
          method: "POST",
          body: JSON.stringify({
            question_id: currentQuestion.id,
            answer: answerText,
            transcript: transcriptNow,
          }),
        }
      );

      const replyText = response.reply?.trim() || "";
      if (replyText) {
        addMessage("ai", replyText);
        await enqueueSpeak(replyText);
      }

      const followup = response.followup?.trim() || "";
      const moveOn = Boolean(response.move_on);

      setIsAiThinking(false);

      if (followup) {
        await askFollowup(followup);
        return;
      }

      if (!moveOn) {
        const fallback = "Could you clarify that a bit more?";
        addMessage("ai", fallback);
        await enqueueSpeak(fallback);
        openListeningWindow(isFollowup ? "followup" : "primary");
        return;
      }

      if (isFollowup) {
        setAnswers((prev) => {
          const next = [...prev];
          const lastAnswer = next[next.length - 1] || "";
          if (lastAnswer) {
            next[next.length - 1] = `${lastAnswer}\nFollow-up: ${answerText}`.trim();
          }
          return next;
        });
      }

      await requestNextQuestion(answerText, transcriptNow);
    } catch (err) {
      console.error("Answer submission failed:", err);
      setIsAiThinking(false);
      
      const fallback = "I am having trouble processing that. Can you explain it again?";
      addMessage("ai", fallback);
      await enqueueSpeak(fallback);
      openListeningWindow(isFollowup ? "followup" : "primary");
    }
  };

  const requestMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setMediaStream(stream);
      setMediaError(null);
      console.log("Media stream acquired");
      return stream;
    } catch (err) {
      console.error("Media permission denied:", err);
      setMediaError("Camera + microphone permissions are required for the interview.");
      return null;
    }
  };

  const beginInterview = async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    
    console.log("Beginning interview");
    setPhase("intro");
    
    await avatarRef.current?.enableAudio();
    
    const greeting = `Hello ${auth.user?.full_name ?? "there"}, how are you doing today? Let's begin your interview.`;
    addMessage("ai", greeting);
    await enqueueSpeak(greeting);
    
    if (!micMutedRef.current) {
      openListeningWindow("greeting");
    } else {
      await requestNextQuestion();
    }
  };

  const startInterview = async () => {
    const stream = mediaStream ?? (await requestMedia());
    if (!stream) return;
    
    await avatarRef.current?.enableAudio();
    setSpeechError(null);
    setCountdown(10);
  };

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (!countdown && countdown !== 0) return;
    if (countdown === 0) {
      setCountdown(null);
      setHasBegun(true);
      return;
    }
    const timer = window.setTimeout(() => {
      setCountdown((prev) => (prev === null ? null : prev - 1));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  useEffect(() => {
    if (!hasBegun) return;
    setStatus("running");
    beginInterview();
  }, [hasBegun]);

  useEffect(() => {
    micMutedRef.current = micMuted;
  }, [micMuted]);

  useEffect(() => {
    hasBegunRef.current = hasBegun;
  }, [hasBegun]);

  useEffect(() => {
    micLevelRef.current = micLevel;
  }, [micLevel]);

  useEffect(() => {
    if (!mediaStream || !videoRef.current) return;
    videoRef.current.srcObject = mediaStream;
    videoRef.current.play().catch(() => undefined);
  }, [mediaStream]);

  useEffect(() => {
    if (!mediaStream) return;
    mediaStream.getVideoTracks().forEach((track) => {
      track.enabled = cameraEnabled;
    });
  }, [mediaStream, cameraEnabled]);

  useEffect(() => {
    if (!mediaStream) return;
    mediaStream.getAudioTracks().forEach((track) => {
      track.enabled = !micMuted;
    });
  }, [mediaStream, micMuted]);

  useEffect(() => {
    if (!mediaStream) return;
    
    const audioContext = new AudioContext();
    audioContext.resume().catch(() => undefined);
    const source = audioContext.createMediaStreamSource(mediaStream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    source.connect(analyser);

    let rafId = 0;
    const tick = () => {
      analyser.getByteFrequencyData(dataArray);
      const avg = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
      setMicLevel(micMuted ? 0 : avg / 255);
      rafId = window.requestAnimationFrame(tick);
    };

    tick();

    return () => {
      window.cancelAnimationFrame(rafId);
      source.disconnect();
      analyser.disconnect();
      audioContext.close();
    };
  }, [mediaStream, micMuted]);

  useEffect(() => {
    return () => {
      mediaStream?.getTracks().forEach((track) => track.stop());
      stopRecognition();
      cleanupStreamingStt();
    };
  }, [mediaStream]);

  useEffect(() => {
    if (useStreamingStt) {
      setVoiceSupported(true);
      return;
    }

    const SpeechRecognitionImpl =
      (window as typeof window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition ||
      (window as typeof window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition;
    
    if (!SpeechRecognitionImpl) {
      console.warn("Speech recognition not supported");
      return;
    }

    const rec = new SpeechRecognitionImpl();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = true;

    rec.onresult = (event) => {
      if (!listeningWindowRef.current || micMutedRef.current) return;
      if (Date.now() - lastAiSpokeAtRef.current < 2000) return;
      
      lastVoiceAtRef.current = Date.now();
      let interim = "";
      
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0].transcript.trim();
        
        if (result.isFinal && transcript) {
          const normalized = transcript.toLowerCase();
          if (normalized !== lastFinalChunkRef.current) {
            sessionFinalRef.current = `${sessionFinalRef.current} ${transcript}`.trim();
            lastFinalChunkRef.current = normalized;
          }
        } else if (!result.isFinal) {
          interim += transcript;
        }
      }
      
      sessionInterimRef.current = interim;
      const combined = `${sessionFinalRef.current} ${sessionInterimRef.current}`.trim();
      
      if (listeningTargetRef.current === "followup") {
        currentFollowupRef.current = combined;
      } else {
        currentAnswerRef.current = combined;
      }
      
      setLiveTranscript(combined);
    };

    rec.onend = () => {
      recognitionActiveRef.current = false;
      if (!endedRef.current && hasBegunRef.current && !micMutedRef.current && listeningWindowRef.current) {
        window.setTimeout(() => startRecognition(), 300);
      }
    };

    rec.onerror = (event: any) => {
      if (!listeningWindowRef.current) return;
      
      const errorCode = event?.error || "speech_error";
      console.error("Speech recognition error:", errorCode);
      
      if (errorCode === "not-allowed" || errorCode === "service-not-allowed") {
        setSpeechError("Microphone permission blocked. Please allow mic access and retry.");
      } else if (errorCode === "no-speech") {
        setSpeechError("No speech detected. Please speak clearly into the mic.");
      } else if (errorCode !== "aborted") {
        setSpeechError(`Speech recognition error: ${errorCode}`);
      }
    };

    setRecognition(rec);
    setVoiceSupported(true);

    if (pendingRecognitionStartRef.current) {
      try {
        if (listeningWindowRef.current) {
          rec.start();
          recognitionActiveRef.current = true;
          pendingRecognitionStartRef.current = false;
        }
      } catch (err) {
        console.error("Failed to start pending recognition:", err);
      }
    }
  }, [useStreamingStt]);

  // Auto-finalize answer when silence detected
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (!listeningWindowRef.current || micMutedRef.current) return;
      
      const now = Date.now();
      const hasTranscript =
        (listeningTargetRef.current === "followup" ? currentFollowupRef.current : currentAnswerRef.current).trim();
      
      if (!hasTranscript) return;
      
      // User is still speaking
      if (micLevelRef.current > 0.02) {
        lastVoiceAtRef.current = now;
        return;
      }
      
      // 9 seconds of silence after speaking = finalize
      if (now - lastVoiceAtRef.current > 9000) {
        console.log("Auto-finalizing answer due to silence");
        finalizeAnswer();
      }
    }, 300);
    
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!hasBegun || status !== "running") return;
    const timer = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [status, hasBegun]);

  useEffect(() => {
    if (phase !== "completed" || status === "completed") return;
    
    const timeout = window.setTimeout(() => {
      completeInterview();
    }, 1200);
    
    return () => window.clearTimeout(timeout);
  }, [phase, status]);

  const completeInterview = async () => {
    console.log("Completing interview with", answers.length, "answers");
    
    const transcript = buildTranscript(messagesRef.current);
    
    try {
      const response = await apiFetch<InterviewResponse>(`/api/candidate/interviews/${interviewId}/complete`, {
        method: "POST",
        body: JSON.stringify({
          answers,
          transcript,
          recording_url: null,
        }),
      });
      
      setStatus("completed");
      setPhase("completed");
      setResult(response.interview);
      endedRef.current = true;
      stopRecognition();
      cleanupStreamingStt();
      
      console.log("Interview completed, score:", response.interview.overall_score);
      navigate(`/candidate/interview/${interviewId}/report`, { replace: true });
    } catch (err) {
      console.error("Failed to complete interview:", err);
      setError((err as Error).message);
    }
  };

  const progress = useMemo(() => {
    if (!totalCount) return 0;
    return Math.round((askedCount / totalCount) * 100);
  }, [askedCount, totalCount]);

  if (error) {
    return (
      <Card className="space-y-3">
        <div className="text-danger font-semibold">Interview Error</div>
        <div className="text-sm text-textMuted">{error}</div>
        <Button variant="secondary" onClick={() => navigate("/candidate/interviews")}>
          Back to Interviews
        </Button>
      </Card>
    );
  }

  if (!voiceSupported) {
    return (
      <Card className="space-y-3 text-sm text-textMuted">
        <div className="text-white">Live voice interview requires real-time speech recognition</div>
        <div>Your browser does not support speech recognition. Please use Chrome or Edge.</div>
        <Button variant="secondary" onClick={() => navigate("/candidate/interviews")}>
          Back to Interviews
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-white">Live AI Interview</div>
          <div className="text-xs text-textMuted">HireNexus - Secure voice interview</div>
        </div>
        <div className="flex items-center gap-2 text-xs text-textMuted">
          <span className="rounded-full border border-border bg-panel px-3 py-1">Phase: {phase}</span>
          <span className="rounded-full border border-border bg-panel px-3 py-1">Timer: {formatTime(elapsedSeconds)}</span>
          <span className="rounded-full border border-border bg-panel px-3 py-1">Progress {progress}%</span>
          <span className="rounded-full border border-border bg-panel px-3 py-1">
            {isRecording ? "Listening" : isAiSpeaking ? "AI Speaking" : isAiThinking ? "AI Thinking" : "Idle"}
          </span>
          {useStreamingStt && (
            <span className="rounded-full border border-border bg-panel px-3 py-1">STT: {sttStatus}</span>
          )}
        </div>
      </div>

      {speechError && (
        <div className="rounded-xl border border-border bg-panelMuted px-4 py-2 text-xs text-danger">
          {speechError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.9fr_1fr]">
        <Card className="relative overflow-hidden border border-border bg-panel p-4">
          <div className="relative aspect-video overflow-hidden rounded-2xl border border-border bg-panelMuted">
            <TalkingHeadAvatar ref={avatarRef} />
            <div className="absolute left-4 top-4 rounded-full border border-border bg-panel px-3 py-1 text-[11px] text-textMuted">
              AI Interviewer
            </div>
            <div className="absolute bottom-4 left-4 flex items-center gap-2 rounded-full border border-border bg-panel px-3 py-1 text-[11px] text-textMuted">
              <span className={`h-2 w-2 rounded-full ${isAiSpeaking ? "bg-accent" : "bg-border"}`} />
              {isAiThinking ? "Thinking" : isAiSpeaking ? "Speaking" : isRecording ? "Listening" : "Idle"}
              <div className="flex items-end gap-1">
                {[0.4, 0.7, 1].map((scale) => (
                  <span
                    key={scale}
                    className={`w-1 rounded-full ${isAiSpeaking ? "bg-accent" : "bg-border"} ${
                      isAiSpeaking ? "animate-pulse" : ""
                    }`}
                    style={{ height: `${8 + (isAiSpeaking ? 12 : 4) * scale}px` }}
                  />
                ))}
              </div>
            </div>
            <div className="absolute top-4 right-4 h-32 w-48 overflow-hidden rounded-xl border border-border bg-black">
              <video
                ref={videoRef}
                className="h-full w-full object-cover"
                muted
                playsInline
                style={{ transform: "scaleX(-1)" }}
              />
              <div className="absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-1 text-[10px] text-white">
                You
              </div>
              <div className="absolute bottom-2 right-2 flex items-end gap-1 rounded-full bg-black/60 px-2 py-1">
                {[0.3, 0.6, 1].map((scale) => (
                  <span
                    key={scale}
                    className={`w-1 rounded-full ${micMuted ? "bg-danger" : "bg-success"}`}
                    style={{ height: `${6 + micLevel * 16 * scale}px` }}
                  />
                ))}
              </div>
              {!cameraEnabled && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/70 text-xs text-white">
                  Camera Off
                </div>
              )}
            </div>
          </div>

          {!hasBegun && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 rounded-2xl bg-black/70 text-center text-sm text-textMuted">
              <div className="text-lg font-semibold text-white">Ready to start your live interview?</div>
              <div>Camera and microphone will turn on for a real-time conversation.</div>
              {mediaError && <div className="text-danger">{mediaError}</div>}
              <div className="flex gap-3">
                <Button variant="secondary" onClick={startInterview}>
                  Start Interview
                </Button>
                <Button variant="ghost" onClick={() => avatarRef.current?.enableAudio()}>
                  Join with Audio
                </Button>
              </div>
            </div>
          )}

          {countdown !== null && (
            <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/80">
              <div className="text-5xl font-bold text-white">{countdown}</div>
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-textMuted">
            <span className="rounded-full border border-border bg-panelMuted px-3 py-1">
              Question {askedCount || 1} / {totalCount}
            </span>
            {currentQuestion && (
              <span className="rounded-full border border-border bg-panelMuted px-3 py-1">
                {currentQuestion.category} · {currentQuestion.difficulty}
              </span>
            )}
            <span className="rounded-full border border-border bg-panelMuted px-3 py-1">Target: 10-15 min</span>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <Button variant="ghost" onClick={() => setCaptionsOn((prev) => !prev)}>
                {captionsOn ? "Hide Captions" : "Show Captions"}
              </Button>
              {isRecording && !finalizingRef.current && (
                <Button variant="secondary" onClick={finalizeAnswer}>
                  Send Answer
                </Button>
              )}
              <Button
                variant={micMuted ? "ghost" : "primary"}
                onClick={() => {
                  if (micMuted) {
                    setMicMuted(false);
                    if (hasBegun) openListeningWindow(followupText ? "followup" : "primary");
                  } else {
                    setMicMuted(true);
                    closeListeningWindow();
                  }
                }}
              >
                {micMuted ? "Unmute" : "Mute"}
              </Button>
              <Button
                variant={cameraEnabled ? "ghost" : "primary"}
                onClick={() => setCameraEnabled((prev) => !prev)}
              >
                {cameraEnabled ? "Camera On" : "Camera Off"}
              </Button>
              <Button variant="secondary" onClick={completeInterview}>
                End Interview
              </Button>
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="space-y-3">
            <div className="text-sm text-textMuted">Interview Insights</div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-panelMuted p-4">
                <div className="text-xs text-textMuted">AI Video Score</div>
                <div className="mt-2 text-2xl font-semibold text-white">
                  {result?.overall_score ? `${result.overall_score.toFixed(0)}%` : "--"}
                </div>
                <div className="mt-3 h-2 w-full rounded-full bg-border/60">
                  <div
                    className="h-2 rounded-full bg-accent"
                    style={{ width: `${result?.overall_score ?? 0}%` }}
                  />
                </div>
              </div>
              <div className="rounded-xl border border-border bg-panelMuted p-4">
                <div className="text-xs text-textMuted">Confidence Score</div>
                <div className="mt-2 text-2xl font-semibold text-white">
                  {result?.confidence_score ? `${result.confidence_score.toFixed(0)}%` : "--"}
                </div>
                <div className="mt-3 h-2 w-full rounded-full bg-border/60">
                  <div
                    className="h-2 rounded-full bg-success"
                    style={{ width: `${result?.confidence_score ?? 0}%` }}
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card className="space-y-3">
            <div className="text-sm text-textMuted">Current Prompt</div>
            <div className="text-base font-semibold text-white">{currentQuestion?.question ?? "Waiting..."}</div>
          </Card>

          <Card className="space-y-3">
            <div className="text-sm text-textMuted">Live Transcript</div>
            <div className="rounded-xl border border-border bg-panelMuted p-3 text-xs text-text">
              {liveTranscript || "Listening..."}
            </div>
          </Card>

          <Card className="space-y-3">
            <div className="text-sm text-textMuted">Conversation</div>
            <div className="max-h-[280px] space-y-3 overflow-auto text-xs text-textMuted">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === "candidate" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[90%] rounded-lg px-3 py-2 text-xs ${
                      msg.role === "candidate" ? "bg-accent text-white" : "bg-panel text-text"
                    }`}
                  >
                    <div className="text-[10px] text-textMuted">
                      {msg.role === "candidate" ? "You" : "AI Interviewer"}
                    </div>
                    <div>{msg.content}</div>
                  </div>
                </div>
              ))}
              {isAiThinking && <div className="text-xs text-textMuted">AI is preparing a follow-up...</div>}
            </div>
          </Card>
        </div>
      </div>

      {captionsOn && lastMessage && (
        <div className="rounded-2xl border border-border bg-panelMuted px-4 py-3 text-sm text-textMuted">
          <div className="text-[10px] uppercase text-textMuted">Live captions</div>
          <div className="mt-2 text-text">
            {lastMessage.role === "ai" ? "AI:" : "You:"} {lastMessage.content}
          </div>
        </div>
      )}

      {result && (
        <Card className="space-y-3">
          <div className="text-white">Interview Report</div>
          <div className="grid gap-2 text-sm text-textMuted md:grid-cols-2">
            <div>Overall Score: {result.overall_score?.toFixed(1)}</div>
            <div>Confidence Score: {result.confidence_score?.toFixed(1)}</div>
          </div>
          <Button
            variant="secondary"
            onClick={() => window.open(`${baseUrl}/api/candidate/interviews/${interviewId}/report.pdf`, "_blank")}
          >
            Download Report PDF
          </Button>
        </Card>
      )}
    </div>
  );
};
