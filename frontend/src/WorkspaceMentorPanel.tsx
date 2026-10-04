import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { BrainCircuit, Send, Sparkles, X } from "lucide-react";

type MentorMessage = { role: "user" | "assistant"; content: string };

type LearningPhase =
  | "observe"
  | "reason"
  | "decide"
  | "implement"
  | "validate"
  | "explain"
  | "completed";

type WorkspaceLearningLoop = {
  loop_id: string;
  stage: "prepare";
  finding_index: number;
  skill_name: string;
  target_type: "column" | "dataset";
  target_name: string | null;
  current_phase: LearningPhase;
  completed_phases: Exclude<LearningPhase, "completed">[];
  status: "active" | "completed";
  trusted_validation: Record<string, unknown>;
};

type Props = {
  workspaceId: string;
  sessionId: string | null;
  language: "en" | "nl" | "tr";
  contextualPrompt?: string | null;
  contextualPromptKey?: number;
  uiContext?: Record<string, unknown> | null;
  learningLoopFindingIndex?: number | null;
  learningLoopKey?: number;
  workspaceRevision?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export default function WorkspaceMentorPanel({
  workspaceId,
  sessionId,
  language,
  contextualPrompt,
  contextualPromptKey,
  uiContext,
  learningLoopFindingIndex = null,
  learningLoopKey = 0,
  workspaceRevision = 0,
  open,
  onOpenChange,
}: Props) {
  const copy = {
    en: { title:"DataPilot Mentor", subtitle:"Workspace-aware senior mentor", placeholder:"Ask about your current work...", send:"Send", empty:"I follow this workspace, its data-quality findings, notebook and pipeline. Ask me what to investigate or do next.", close:"Close", collapse:"Collapse", expand:"Open mentor", thinking:"Thinking...", learningLoop:"Guided learning loop", learningLoopLoading:"Preparing learning step...", phase:"Phase", workbenchGate:"This phase advances only after a real Workbench transformation and deterministic validation.", completed:"Learning loop completed" },
    nl: { title:"DataPilot Mentor", subtitle:"Senior mentor met werkruimtecontext", placeholder:"Vraag iets over je huidige werk...", send:"Versturen", empty:"Ik volg deze werkruimte, de datakwaliteitsbevindingen, het notebook en de pipeline. Vraag wat je nu moet onderzoeken of doen.", close:"Sluiten", collapse:"Inklappen", expand:"Mentor openen", thinking:"Nadenken...", learningLoop:"Begeleide leerloop", learningLoopLoading:"Leerstap voorbereiden...", phase:"Fase", workbenchGate:"Deze fase gaat alleen verder na een echte Workbench-transformatie en deterministische validatie.", completed:"Leerloop voltooid" },
    tr: { title:"DataPilot Mentor", subtitle:"Çalışma alanını bilen kıdemli mentor", placeholder:"Mevcut çalışman hakkında sor...", send:"Gönder", empty:"Bu çalışma alanını, veri kalitesi bulgularını, notebook'u ve pipeline'ı takip ediyorum. Şimdi neyi incelemen veya yapman gerektiğini sorabilirsin.", close:"Kapat", collapse:"Daralt", expand:"Mentoru aç", thinking:"Düşünüyor...", learningLoop:"Yönlendirmeli öğrenme döngüsü", learningLoopLoading:"Öğrenme adımı hazırlanıyor...", phase:"Aşama", workbenchGate:"Bu aşama yalnızca gerçek bir Workbench dönüşümü ve deterministik doğrulama sonrasında ilerler.", completed:"Öğrenme döngüsü tamamlandı" },
  }[language];

  const [messages,setMessages]=useState<MentorMessage[]>([]);
  const [learningMessages,setLearningMessages]=useState<MentorMessage[]>([]);
  const [learningLoop,setLearningLoop]=useState<WorkspaceLearningLoop|null>(null);
  const [learningLoopLoading,setLearningLoopLoading]=useState(false);
  const [input,setInput]=useState("");
  const [loading,setLoading]=useState(false);
  const endRef=useRef<HTMLDivElement|null>(null);

  useEffect(()=>{
    if(!sessionId){ setMessages([]); return; }
    let cancelled=false;
    fetch(`http://127.0.0.1:8000/chat/${sessionId}/history`)
      .then(async r=>{ if(!r.ok) throw new Error(); return r.json(); })
      .then(data=>{ if(!cancelled) setMessages((data.messages ?? []).filter((m:MentorMessage)=>m.role==="user"||m.role==="assistant")); })
      .catch(()=>{ if(!cancelled) setMessages([]); });
    return ()=>{ cancelled=true; };
  },[sessionId]);

  useEffect(()=>{
    if(contextualPrompt && contextualPromptKey){
      onOpenChange(true); setInput(contextualPrompt);
    }
  },[contextualPrompt,contextualPromptKey,onOpenChange]);

  useEffect(()=>{
    if(learningLoopFindingIndex===null) return;

    let cancelled=false;
    setLearningLoopLoading(true);
    onOpenChange(true);

    fetch(
      `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/findings/${learningLoopFindingIndex}/learning-loop?language=${language}`,
      { method:"POST" }
    )
      .then(async response=>{
        const data=await response.json();
        if(!response.ok) throw new Error(data.detail || "Learning loop could not be started.");
        return data;
      })
      .then(data=>{
        if(cancelled) return;

        const nextLoop=data.loop as WorkspaceLearningLoop;
        const prompt=String(data.mentor_prompt ?? "");

        setLearningLoop(nextLoop);
        setLearningMessages(prev=>{
          if(!prompt) return prev;

          const last=prev.at(-1);
          if(last?.role==="assistant" && last.content===prompt){
            return prev;
          }

          return [
            ...prev,
            { role:"assistant", content:prompt },
          ];
        });
      })
      .catch(error=>{
        if(cancelled) return;
        setLearningMessages(prev=>[
          ...prev,
          {
            role:"assistant",
            content:error instanceof Error
              ? error.message
              : "Learning loop could not be started.",
          },
        ]);
      })
      .finally(()=>{
        if(!cancelled) setLearningLoopLoading(false);
      });

    return ()=>{ cancelled=true; };
  },[
    learningLoopFindingIndex,
    learningLoopKey,
    workspaceRevision,
    workspaceId,
    onOpenChange,
  ]);

  useEffect(()=>{ endRef.current?.scrollIntoView({behavior:"smooth"}); },[messages,learningMessages,loading,learningLoopLoading]);

  async function submit(event?:FormEvent){
    event?.preventDefault();
    const message=input.trim();
    if(!message || !sessionId || loading) return;

    const structuredPhase =
      learningLoop?.status==="active" &&
      (
        learningLoop.current_phase==="observe" ||
        learningLoop.current_phase==="reason" ||
        learningLoop.current_phase==="decide" ||
        learningLoop.current_phase==="explain"
      );

    setInput("");
    setLoading(true);

    if(structuredPhase && learningLoop){
      setLearningMessages(prev=>[
        ...prev,
        {role:"user",content:message},
      ]);

      try{
        const response=await fetch(
          `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/findings/${learningLoop.finding_index}/learning-loop/${learningLoop.loop_id}/respond`,
          {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({response:message}),
          }
        );

        const data=await response.json();

        if(!response.ok){
          throw new Error(
            data.detail ||
            "Learning response could not be reviewed."
          );
        }

        setLearningLoop(
          data.loop as WorkspaceLearningLoop
        );

        setLearningMessages(prev=>[
          ...prev,
          {
            role:"assistant",
            content:String(data.mentor_response ?? ""),
          },
        ]);
      }catch(error){
        setLearningMessages(prev=>[
          ...prev,
          {
            role:"assistant",
            content:error instanceof Error
              ? error.message
              : "Learning response could not be reviewed.",
          },
        ]);
      }finally{
        setLoading(false);
      }

      return;
    }

    setMessages(prev=>[...prev,{role:"user",content:message}]);
    try{
      const response=await fetch("http://127.0.0.1:8000/chat",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          session_id:sessionId,
          learner_id:"demo-learner",
          workspace_id:workspaceId,
          message,
          ui_context:uiContext ?? null,
        }),
      });
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail || "Mentor response failed.");
      setMessages(prev=>[...prev,{role:"assistant",content:data.reply}]);
    }catch(error){
      setMessages(prev=>[...prev,{role:"assistant",content:error instanceof Error?error.message:"Mentor response failed."}]);
    }finally{ setLoading(false); }
  }

  if(!open) return <button className="mentor-panel-launcher" type="button" aria-label={copy.expand} title={copy.expand} onClick={()=>onOpenChange(true)}><span className="mentor-launcher-presence" aria-hidden="true"/><BrainCircuit size={22}/><span className="mentor-launcher-badge">Mentor</span></button>;

  return <aside className="workspace-mentor-panel">
    <header className="workspace-mentor-header">
      <div><BrainCircuit size={20}/><span><strong>{copy.title}</strong><small>{copy.subtitle}</small></span></div>
      <span className="workspace-mentor-header-actions">
        <button type="button" title={copy.close} onClick={()=>onOpenChange(false)}><X size={17}/></button>
      </span>
    </header>
    <>
      {learningLoop && (
        <div className="mentor-learning-loop-status">
          <div>
            <span>{copy.learningLoop}</span>
            <strong>
              {learningLoop.skill_name.replaceAll("_"," ")}
            </strong>
          </div>

          <span className={
            "mentor-learning-phase " +
            (
              learningLoop.status==="completed"
                ? "completed"
                : ""
            )
          }>
            {learningLoop.status==="completed"
              ? copy.completed
              : `${copy.phase}: ${
                  {
                    en: {
                      observe: "Observe",
                      reason: "Reason",
                      decide: "Decide",
                      implement: "Implement",
                      validate: "Validate",
                      explain: "Explain",
                      completed: "Completed",
                    },
                    nl: {
                      observe: "Observeren",
                      reason: "Redeneren",
                      decide: "Beslissen",
                      implement: "Uitvoeren",
                      validate: "Valideren",
                      explain: "Uitleggen",
                      completed: "Voltooid",
                    },
                    tr: {
                      observe: "Gözlemle",
                      reason: "Akıl yürüt",
                      decide: "Karar ver",
                      implement: "Uygula",
                      validate: "Doğrula",
                      explain: "Açıkla",
                      completed: "Tamamlandı",
                    },
                  }[language][learningLoop.current_phase]
                }`}
          </span>
        </div>
      )}

      <div className="workspace-mentor-messages">
        {messages.length===0 && learningMessages.length===0 && <div className="workspace-mentor-empty"><Sparkles size={18}/><p>{copy.empty}</p></div>}
        {messages.map((m,i)=><div key={`chat-${i}`} className={`workspace-mentor-message ${m.role}`}><span>{m.content}</span></div>)}
        {learningMessages.map((m,i)=><div key={`learning-${i}`} className={`workspace-mentor-message ${m.role} learning`}><span>{m.content}</span></div>)}
        {learningLoop && learningLoop.status==="active" && (learningLoop.current_phase==="implement" || learningLoop.current_phase==="validate") && (
          <div className="mentor-learning-gate">{copy.workbenchGate}</div>
        )}
        {(loading || learningLoopLoading) && <div className="workspace-mentor-message assistant"><span>{learningLoopLoading?copy.learningLoopLoading:copy.thinking}</span></div>}
        <div ref={endRef}/>
      </div>
      <form className="workspace-mentor-composer" onSubmit={submit}>
        <textarea value={input} onChange={e=>setInput(e.target.value)} placeholder={copy.placeholder} rows={2}
          onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();void submit();}}}/>
        <button type="submit" disabled={!input.trim()||loading} title={copy.send}><Send size={17}/></button>
      </form>
    </>
  </aside>;
}
