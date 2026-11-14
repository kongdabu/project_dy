"use client";

import { useEffect, useId, useState } from "react";
import { Code2, Network, Sparkles } from "lucide-react";

interface MindmapTabProps {
  mermaidCode: string;
  onGenerateSummary: () => void;
}

export default function MindmapTab({ mermaidCode, onGenerateSummary }: MindmapTabProps) {
  const [svg, setSvg] = useState("");
  const [renderError, setRenderError] = useState("");
  const [showCode, setShowCode] = useState(false);
  const uniqueId = useId().replace(/:/g, "");

  useEffect(() => {
    let cancelled = false;
    async function renderDiagram() {
      if (!mermaidCode) {
        setSvg("");
        return;
      }
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "neutral",
          securityLevel: "strict",
        });
        const cleanCode = mermaidCode
          .replace(/^```mermaid\s*/i, "")
          .replace(/```$/i, "")
          .trim();
        const { svg: rendered } = await mermaid.render(`mindmap_${uniqueId}`, cleanCode);
        if (!cancelled) {
          setSvg(rendered);
          setRenderError("");
        }
      } catch (err) {
        if (!cancelled) {
          setRenderError(err instanceof Error ? err.message : "마인드맵 렌더링 실패");
        }
      }
    }
    renderDiagram();
    return () => {
      cancelled = true;
    };
  }, [mermaidCode, uniqueId]);

  if (!mermaidCode) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-16 text-center">
        <Network className="h-10 w-10 text-teal-600" />
        <h3 className="mt-3 text-base font-bold text-slate-900">AI 마인드맵 (Tikonote 스타일)</h3>
        <p className="mt-1 max-w-md text-xs text-slate-500">
          [요약·용어] 탭에서 AI 분석을 실행하면 병태생리 및 치료 흐름도가 자동으로 생성됩니다.
        </p>
        <button
          type="button"
          onClick={onGenerateSummary}
          className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white hover:bg-teal-700"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>요약 및 마인드맵 생성</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900">개념 및 기전 AI 마인드맵</h3>
          <p className="text-xs text-slate-500">복잡한 의학 기전과 진단/치료 흐름을 한눈에 파악하세요.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCode((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <Code2 className="h-3.5 w-3.5" />
          <span>{showCode ? "다이어그램 보기" : "Mermaid 코드"}</span>
        </button>
      </div>

      {showCode ? (
        <pre className="overflow-auto rounded-2xl border border-slate-200 bg-slate-900 p-4 text-xs text-slate-100">
          {mermaidCode}
        </pre>
      ) : renderError ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800">
          <p className="font-bold">다이어그램 구문 파싱 중 문제가 발생했습니다.</p>
          <pre className="mt-2 whitespace-pre-wrap text-[11px]">{mermaidCode}</pre>
        </div>
      ) : (
        <div
          className="overflow-auto rounded-2xl border border-slate-200 bg-white p-6"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
    </div>
  );
}

