import { Canvas, useFrame } from "@react-three/fiber";
import { Center, Environment, OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";

type AvatarState = "listening" | "thinking" | "speaking";

type AvatarProps = {
  state: AvatarState;
};

const READY_PLAYER_ME_URL =
  "https://models.readyplayer.me/69823a8647a75ab0c8f581ba.glb?morphTargets=ARKit,Oculus+Visemes,mouthOpen,mouthSmile,eyesClosed,eyesLookUp,eyesLookDown";

const stateColor = (state: AvatarState) => {
  if (state === "speaking") return "#7c3aed";
  if (state === "thinking") return "#22c55e";
  return "#94a3b8";
};

const FallbackAvatar = ({ state }: AvatarProps) => {
  const group = useRef<THREE.Group>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const color = useMemo(() => stateColor(state), [state]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (group.current) {
      group.current.rotation.y = Math.sin(t * 0.4) * 0.12;
      group.current.position.y = Math.sin(t * 0.6) * 0.05;
    }
    if (mouth.current) {
      const scale = state === "speaking" ? 0.5 + Math.abs(Math.sin(t * 6)) * 0.6 : 0.25;
      mouth.current.scale.y = scale;
    }
  });

  return (
    <group ref={group}>
      <mesh position={[0, 0.4, 0]}>
        <sphereGeometry args={[0.75, 32, 32]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <mesh position={[0, -0.6, 0]}>
        <cylinderGeometry args={[0.6, 0.75, 0.9, 32]} />
        <meshStandardMaterial color="#1f1f24" />
      </mesh>
      <mesh position={[-0.25, 0.55, 0.55]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#0b0b0f" />
      </mesh>
      <mesh position={[0.25, 0.55, 0.55]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#0b0b0f" />
      </mesh>
      <mesh ref={mouth} position={[0, 0.25, 0.58]}>
        <boxGeometry args={[0.25, 0.06, 0.06]} />
        <meshStandardMaterial color="#0b0b0f" />
      </mesh>
    </group>
  );
};

const ReadyPlayerAvatar = ({ state }: AvatarProps) => {
  const group = useRef<THREE.Group>(null);
  const { scene } = useGLTF(READY_PLAYER_ME_URL);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (group.current) {
      group.current.rotation.y = Math.sin(t * 0.35) * 0.08;
      group.current.position.y = Math.sin(t * 0.6) * 0.02;
    }

    scene.traverse((child) => {
      if (!(child as THREE.Mesh).isMesh) return;
      const mesh = child as THREE.Mesh;
      const dict = (mesh as any).morphTargetDictionary as Record<string, number> | undefined;
      const influences = (mesh as any).morphTargetInfluences as number[] | undefined;
      if (!dict || !influences) return;

      const mouthTargets = [
        "mouthOpen",
        "viseme_aa",
        "viseme_E",
        "viseme_O",
        "viseme_U",
        "JawOpen",
      ];
      const active = mouthTargets.find((target) => dict[target] !== undefined);
      if (!active) return;

      const idx = dict[active];
      const intensity = state === "speaking" ? 0.35 + Math.abs(Math.sin(t * 7)) * 0.45 : 0.04;
      influences[idx] = intensity;
    });
  });

  return (
    <Center>
      <primitive ref={group} object={scene} position={[0, -1.25, 0]} scale={1.25} />
    </Center>
  );
};

export const VideoAvatar = ({ state }: { state: AvatarState }) => {
  const webglSupported = typeof window !== "undefined" && !!window.WebGLRenderingContext;

  return (
    <div className="h-64 w-full rounded-xl border border-border bg-panel">
      {webglSupported ? (
        <Canvas camera={{ position: [0, 0.4, 2.4], fov: 35 }}>
          <ambientLight intensity={0.9} />
          <directionalLight position={[2, 3, 4]} intensity={1.2} />
          <directionalLight position={[-2, 2, 2]} intensity={0.6} />
          <Suspense fallback={<FallbackAvatar state={state} />}>
            <ReadyPlayerAvatar state={state} />
            <Environment preset="city" />
          </Suspense>
          <OrbitControls enableZoom={false} enablePan={false} />
        </Canvas>
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-textMuted">
          3D avatar unavailable in this browser.
        </div>
      )}
    </div>
  );
};

useGLTF.preload(READY_PLAYER_ME_URL);
