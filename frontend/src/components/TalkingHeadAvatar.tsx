// file name is TalkingHeadAvatar.tsx
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { TalkingHead } from "../vendor/talkinghead.mjs";
import { apiFetch } from "../lib/api";

export type TalkingHeadHandle = {
  speak: (text: string) => Promise<void>;
  enableAudio: () => Promise<void>;
};

type TalkingHeadAvatarProps = {
  onReady?: () => void;
};

type WordMark = {
  word: string;
  time: number;
};

type VoiceTtsResponse = {
  audio_base64: string;
  word_marks: WordMark[];
  voice_id?: string;
  engine?: string;
  language_code?: string;
};

const READY_PLAYER_ME_URL =
  "https://models.readyplayer.me/69823a8647a75ab0c8f581ba.glb?morphTargets=ARKit,Oculus+Visemes,mouthOpen,mouthSmile,eyesClosed,eyesLookUp,eyesLookDown";

const HEADTTS_MODULE = "https://esm.sh/@met4citizen/headtts@1.2.0?bundle";

const HEADTTS_WORKER = "https://cdn.jsdelivr.net/npm/@met4citizen/headtts@1.2.0/worker-tts.mjs";

const HEADTTS_DICTIONARY = "https://cdn.jsdelivr.net/npm/@met4citizen/headtts@1.2.0/dictionaries";

const HEADTTS_VOICE = "af_bella";

const TTS_PROVIDER = import.meta.env.VITE_TTS_PROVIDER || "local";
const AVATAR_DEBUG = import.meta.env.DEV && import.meta.env.VITE_AVATAR_DEBUG === "true";

const debugLog = (...args: unknown[]) => {
  if (!AVATAR_DEBUG) return;
  console.debug(...args);
};

const pickPreferredVoice = (voices: SpeechSynthesisVoice[]) => {
  const preferred = [
    "Google Indian English Female",
    "Google English (India)",
    "Microsoft Heera",
    "Heera",
    "Aditi",
    "Raveena",
    "Google UK English Female",
    "Google US English",
    "Samantha",
    "Microsoft Zira",
    "Zira",
    "Jenny",
    "Female",
  ];
  
  for (const name of preferred) {
    const voice = voices.find((item) => item.name.includes(name));
    if (voice) {
      debugLog("Selected preferred voice:", voice.name);
      return voice;
    }
  }
  
  const femaleVoice = voices.find((voice) => /female/i.test(voice.name));
  if (femaleVoice) {
    debugLog("Selected female voice:", femaleVoice.name);
    return femaleVoice;
  }
  
  if (voices.length > 0) {
    debugLog("Selected default voice:", voices[0].name);
    return voices[0];
  }
  
  return null;
};

const base64ToArrayBuffer = (base64: string) => {
  const binary = window.atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
};

export const TalkingHeadAvatar = forwardRef<TalkingHeadHandle, TalkingHeadAvatarProps>(({ onReady }, ref) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const headRef = useRef<any>(null);
  const ttsRef = useRef<any>(null);
  const voicesWarnedRef = useRef(false);
  const voicesReadyRef = useRef(false);
  const pendingRef = useRef<{ resolve: () => void; reject: (err: Error) => void } | null>(null);
  const decodeCtxRef = useRef<AudioContext | null>(null);
  const [status, setStatus] = useState("Loading avatar...");
  const [fallbackVoice, setFallbackVoice] = useState<SpeechSynthesisVoice | null>(null);
  const serverTtsEnabled = TTS_PROVIDER === "polly";
  const speakingRef = useRef(false);

  const decodeAudio = async (buffer: ArrayBuffer, fallbackText: string) => {
    try {
      const context = decodeCtxRef.current ?? new AudioContext();
      decodeCtxRef.current = context;
      
      // Clone the buffer to avoid detached buffer issues
      const clonedBuffer = buffer.slice(0);
      const decoded = await context.decodeAudioData(clonedBuffer);
      
      debugLog("Audio decoded successfully:", {
        duration: decoded.duration,
        sampleRate: decoded.sampleRate,
        channels: decoded.numberOfChannels
      });
      
      return { audioBuffer: decoded, durationMs: decoded.duration * 1000 };
    } catch (err) {
      console.error("Audio decode failed:", err);
      // Estimate duration based on word count
      const words = Math.max(fallbackText.split(/\s+/).length, 1);
      const estimatedDuration = Math.max(800, words * 320);
      return { audioBuffer: null, durationMs: estimatedDuration };
    }
  };

  const playAudioFallback = async (buffer: ArrayBuffer) => {
    try {
      const blob = new Blob([buffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      await new Promise<void>((resolve, reject) => {
        audio.onended = () => {
          URL.revokeObjectURL(url);
          resolve();
        };
        audio.onerror = (err) => {
          console.error("Audio playback error:", err);
          URL.revokeObjectURL(url);
          reject(err);
        };
        audio.play().catch((err) => {
          console.error("Failed to play audio:", err);
          URL.revokeObjectURL(url);
          reject(err);
        });
      });
    } catch (err) {
      console.error("Fallback audio playback failed:", err);
      throw err;
    }
  };

  const speakWithServerTts = async (text: string) => {
    if (!serverTtsEnabled) {
      return false;
    }
    
    try {
      debugLog("Requesting server TTS for:", text.substring(0, 50) + "...");
      
      const response = await apiFetch<VoiceTtsResponse>("/api/voice/tts", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      
      if (!response.audio_base64) {
        console.error("Server returned empty audio");
        return false;
      }
      
      debugLog("Received TTS response:", {
        audioSize: response.audio_base64.length,
        wordMarks: response.word_marks?.length || 0,
        voice: response.voice_id,
        engine: response.engine
      });
      
      const rawBuffer = base64ToArrayBuffer(response.audio_base64);
      const { audioBuffer, durationMs } = await decodeAudio(rawBuffer, text);
      
      // Extract word timing data
      const marks = response.word_marks || [];
      const words = marks.map((mark) => mark.word);
      const wtimes = marks.map((mark) => mark.time);
      const wdurations = wtimes.map((time, idx) => {
        const next = wtimes[idx + 1] ?? durationMs;
        return Math.max(80, next - time);
      });

      // Try to use avatar speech with lip-sync
      if (headRef.current?.speakAudio && audioBuffer) {
        debugLog("Playing audio with avatar lip-sync");
        
        await new Promise<void>((resolve, reject) => {
          const markerTime = Math.max(durationMs, wtimes[wtimes.length - 1] ?? 0);
          const marker = () => {
            debugLog("Speech marker reached");
            resolve();
          };
          
          try {
            headRef.current.speakAudio(
              {
                audio: audioBuffer,
                words,
                wtimes,
                wdurations,
                markers: [marker],
                mtimes: [markerTime],
              },
              { lipsyncLang: "en" }
            );
            
            // Safety timeout
            window.setTimeout(() => {
              debugLog("Speech timeout reached");
              resolve();
            }, markerTime + 1000);
          } catch (err) {
            console.error("Avatar speakAudio failed:", err);
            reject(err);
          }
        });
        
        return true;
      }

      // Fallback: play audio without lip-sync
      debugLog("Playing audio without lip-sync");
      await playAudioFallback(rawBuffer);
      return true;
      
    } catch (err) {
      console.error("Server TTS failed:", err);
      return false;
    }
  };

  useImperativeHandle(ref, () => ({
    speak: async (text: string) => {
      if (!text?.trim()) {
        console.warn("Empty text provided to speak");
        return;
      }

      if (speakingRef.current) {
        console.warn("Already speaking, queuing is handled externally");
      }
      
      speakingRef.current = true;
      
      try {
        // Try server TTS first
        const serverSpoken = await speakWithServerTts(text);
        if (serverSpoken) {
          debugLog("Server TTS successful");
          return;
        }

        // Try local TTS
        if (ttsRef.current && headRef.current) {
          debugLog("Using local TTS");
          
          const audioPromise = new Promise<void>((resolve, reject) => {
            pendingRef.current = { resolve, reject };
            setTimeout(() => {
              console.error("Local TTS timeout");
              reject(new Error("TTS timeout"));
            }, 15000); // Increased timeout
          });

          await ttsRef.current.synthesize({
            input: text,
            voice: HEADTTS_VOICE,
            language: "en-us",
            speed: 1,
          });

          await audioPromise;
          debugLog("Local TTS successful");
          return;
        }

        // Final fallback: browser speech synthesis
        debugLog("Using browser speech synthesis fallback");
        if ("speechSynthesis" in window) {
          await new Promise<void>((resolve) => {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            
            if (fallbackVoice) {
              utterance.voice = fallbackVoice;
            }
            
            utterance.rate = 0.98;
            utterance.pitch = 1.02;
            utterance.volume = 1.0;
            
            utterance.onend = () => {
              debugLog("Browser speech synthesis completed");
              resolve();
            };
            utterance.onerror = (err) => {
              console.error("Browser speech synthesis error:", err);
              resolve(); // Don't fail, just continue
            };
            
            window.speechSynthesis.speak(utterance);
          });
        }
      } catch (err) {
        console.error("All TTS methods failed:", err);
        // Don't throw - we want to continue the interview
      } finally {
        speakingRef.current = false;
      }
    },
    
    enableAudio: async () => {
      debugLog("Enabling audio contexts");
      
      // Resume local TTS audio context
      const audioCtx = ttsRef.current?.settings?.audioCtx;
      if (audioCtx && audioCtx.state === "suspended") {
        try {
          await audioCtx.resume();
          debugLog("Local TTS audio context resumed");
        } catch (err) {
          console.error("Failed to resume audio context:", err);
        }
      }
      
      // Resume decode audio context
      if (decodeCtxRef.current && decodeCtxRef.current.state === "suspended") {
        try {
          await decodeCtxRef.current.resume();
          debugLog("Decode audio context resumed");
        } catch (err) {
          console.error("Failed to resume decode context:", err);
        }
      }
      
      // Resume browser speech synthesis
      if ("speechSynthesis" in window) {
        try {
          window.speechSynthesis.resume();
          debugLog("Browser speech synthesis resumed");
        } catch (err) {
          console.error("Failed to resume speech synthesis:", err);
        }
      }
    },
  }));

  useEffect(() => {
    if (!("speechSynthesis" in window)) {
      console.warn("Speech synthesis not supported");
      return;
    }
    
    const updateVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      if (voices.length === 0) {
        return;
      }
      voicesReadyRef.current = true;
      
      const choice = pickPreferredVoice(voices);
      if (choice) {
        setFallbackVoice(choice);
      }
    };

    const warnTimer = window.setTimeout(() => {
      const voices = window.speechSynthesis.getVoices();
      if (voices.length === 0 && !voicesWarnedRef.current && !voicesReadyRef.current && !serverTtsEnabled) {
        voicesWarnedRef.current = true;
        console.warn("No voices available after initialization delay");
      }
    }, 3500);
    
    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;
    
    return () => {
      window.clearTimeout(warnTimer);
      if (window.speechSynthesis.onvoiceschanged === updateVoices) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, [serverTtsEnabled]);

  useEffect(() => {
    return () => {
      debugLog("Cleaning up audio contexts");
      decodeCtxRef.current?.close();
      decodeCtxRef.current = null;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const init = async () => {
      try {
        setStatus("Loading 3D avatar...");
        debugLog("Initializing avatar");

        if (!containerRef.current) {
          console.error("Container ref not available");
          return;
        }
        
        headRef.current = new TalkingHead(containerRef.current, {
          lipsyncModules: ["en"],
          cameraView: "head",
        });

        debugLog("Loading avatar model");
        await headRef.current.showAvatar({
          url: READY_PLAYER_ME_URL,
          body: "F",
          avatarMood: "neutral",
          ttsLang: "en-US",
          lipsyncLang: "en",
        });
        
        debugLog("Avatar loaded successfully");

        if (!serverTtsEnabled) {
          const { HeadTTS } = await import(/* @vite-ignore */ HEADTTS_MODULE);

          // Initialize local TTS
          const headttsOptions = {
            workerModule: HEADTTS_WORKER,
            dictionaryURL: HEADTTS_DICTIONARY,
            endpoints: ["webgpu", "wasm"],
            defaultVoice: HEADTTS_VOICE,
            defaultLanguage: "en-us",
            defaultSpeed: 1,
            trace: 0,
          };

          debugLog("Initializing HeadTTS");
          ttsRef.current = new HeadTTS(headttsOptions);

          ttsRef.current.onmessage = (message: any) => {
            if (message?.type === "audio" && headRef.current) {
              debugLog("Received audio from HeadTTS");
              try {
                headRef.current.speakAudio(message.data, { lipsyncLang: "en" });
                pendingRef.current?.resolve();
                pendingRef.current = null;
              } catch (err) {
                console.error("Failed to play HeadTTS audio:", err);
                pendingRef.current?.reject(err as Error);
                pendingRef.current = null;
              }
            }
          };

          try {
            await ttsRef.current.connect();
            await ttsRef.current.setup({ voice: HEADTTS_VOICE, language: "en-us", speed: 1 });
            debugLog("HeadTTS initialized successfully");
          } catch (err) {
            console.error("HeadTTS initialization failed:", err);
            ttsRef.current = null;
            if (isMounted) {
              setStatus("Avatar ready (using fallback audio)");
            }
          }
        } else {
          debugLog("Skipping HeadTTS init because server Polly mode is active");
        }

        if (isMounted) {
          setStatus("");
          debugLog("Avatar initialization complete");
          onReady?.();
        }
      } catch (error) {
        console.error("Avatar initialization error:", error);
        if (isMounted) {
          setStatus("Avatar failed to load. Using audio-only mode.");
        }
      }
    };

    init();

    return () => {
      debugLog("Unmounting avatar component");
      isMounted = false;
      
      // Cleanup
      if (headRef.current) {
        try {
          headRef.current.stop();
        } catch (err) {
          console.error("Failed to stop avatar:", err);
        }
      }
      
      if (ttsRef.current) {
        try {
          ttsRef.current.disconnect();
        } catch (err) {
          console.error("Failed to disconnect TTS:", err);
        }
      }
    };
  }, [onReady, serverTtsEnabled]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />
      {status && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-sm text-white">
          {status}
        </div>
      )}
    </div>
  );
});

TalkingHeadAvatar.displayName = "TalkingHeadAvatar";
