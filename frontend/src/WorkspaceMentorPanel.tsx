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
  message_history: MentorMessage[];
};

type Props = {
  workspaceId: string;
  usageContext?: "personal" | "work";
  dataSensitivity?: "public" | "internal" | "unknown" | "confidential" | "restricted" | null;
  teachingContext?: "generic" | "question_and_code" | "question_code_and_summaries" | null;
  onTeachingContextChange?: (mode: "generic" | "question_and_code" | "question_code_and_summaries") => Promise<void>;
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
  usageContext,
  dataSensitivity,
  teachingContext,
  onTeachingContextChange,
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
    en: { title:"DataPilot Mentor", subtitle:"Workspace-aware senior mentor", placeholder:"Ask about your current work...", learningPlaceholder:"Answer the current learning step...", send:"Send", empty:"I follow this workspace, its data-quality findings, notebook and pipeline. Ask me what to investigate or do next.", learningEmpty:"Start a guided learning step from a data-quality finding.", close:"Close", collapse:"Collapse", expand:"Open mentor", thinking:"Thinking...", chatMode:"Mentor Chat", learningMode:"Guided Learning", learningLoop:"Guided learning loop", learningLoopLoading:"Preparing learning step...", phase:"Phase", workbenchGate:"This phase advances only after a real Workbench transformation and deterministic validation.", completed:"Learning loop completed", restart:"Restart learning loop" },
    nl: { title:"DataPilot Mentor", subtitle:"Senior mentor met werkruimtecontext", placeholder:"Vraag iets over je huidige werk...", learningPlaceholder:"Beantwoord de huidige leerstap...", send:"Versturen", empty:"Ik volg deze werkruimte, de datakwaliteitsbevindingen, het notebook en de pipeline. Vraag wat je nu moet onderzoeken of doen.", learningEmpty:"Start een begeleide leerstap vanuit een datakwaliteitsbevinding.", close:"Sluiten", collapse:"Inklappen", expand:"Mentor openen", thinking:"Nadenken...", chatMode:"Mentorchat", learningMode:"Begeleid leren", learningLoop:"Begeleide leerloop", learningLoopLoading:"Leerstap voorbereiden...", phase:"Fase", workbenchGate:"Deze fase gaat alleen verder na een echte Workbench-transformatie en deterministische validatie.", completed:"Leerloop voltooid", restart:"Leerloop opnieuw starten" },
    tr: { title:"DataPilot Mentor", subtitle:"Çalışma alanını bilen kıdemli mentor", placeholder:"Mevcut çalışman hakkında sor...", learningPlaceholder:"Mevcut öğrenme adımını cevapla...", send:"Gönder", empty:"Bu çalışma alanını, veri kalitesi bulgularını, notebook'u ve pipeline'ı takip ediyorum. Şimdi neyi incelemen veya yapman gerektiğini sorabilirsin.", learningEmpty:"Bir veri kalitesi bulgusundan yönlendirmeli öğrenme adımı başlat.", close:"Kapat", collapse:"Daralt", expand:"Mentoru aç", thinking:"Düşünüyor...", chatMode:"Mentor Chat", learningMode:"Yönlendirmeli Öğrenme", learningLoop:"Yönlendirmeli öğrenme döngüsü", learningLoopLoading:"Öğrenme adımı hazırlanıyor...", phase:"Aşama", workbenchGate:"Bu aşama yalnızca gerçek bir Workbench dönüşümü ve deterministik doğrulama sonrasında ilerler.", completed:"Öğrenme döngüsü tamamlandı", restart:"Öğrenme döngüsünü yeniden başlat" },
  }[language];

  const [messages,setMessages]=useState<MentorMessage[]>([]);
  const [learningMessages,setLearningMessages]=useState<MentorMessage[]>([]);
  const [activeMode,setActiveMode]=useState<"chat"|"learning">("chat");
  const [learningLoop,setLearningLoop]=useState<WorkspaceLearningLoop|null>(null);
  const [learningLoopLoading,setLearningLoopLoading]=useState(false);
  const [input,setInput]=useState("");
  const [loading,setLoading]=useState(false);
  const effectiveTeachingContext = teachingContext ?? (
    dataSensitivity === "public" || dataSensitivity === "internal" ? "question_and_code" : "generic"
  );
  const [teachingDraft, setTeachingDraft] = useState(effectiveTeachingContext);
  const [teachingSaving, setTeachingSaving] = useState(false);
  const [teachingError, setTeachingError] = useState<string | null>(null);
  const protectedData = dataSensitivity === "confidential" || dataSensitivity === "restricted";
  const teachingCopy = {
    tr: {
      title: "Notebook’ta ayrıntılı yardım",
      limited: "Notebook öğretimi genel modda: Bu öğretici yolda sorunun tam metni modele gönderilmiyor; ayrıntılı kod soruları yeterince yanıtlanamayabilir.",
      shared: "Notebook öğretimi, mesajlarını ve son kod denemeni kullanabilir; hatalı deneme tamamlanmış işlem sayılmaz.",
      protected: "Bu verinin koruma sınıfı, bu öğretici yolda harici AI bağlam paylaşımını engelliyor.",
      description: "Ayrıntılı yardım seçeneği, mesajlarını, ilgili sütun adlarını ve son kod denemesini (hata veren denemeler dahil) harici AI sağlayıcısına gönderir. Koddaki diğer sabit değerler ve yorumlar ayıklanır; yerel sözdizimi tanısı ve kayıtlı hata türü paylaşılabilir. Mesaj veya kodda yazdığın değerler de paylaşılabilir. Kontrol özetlerini de seçersen proje hedefi, öğrenme tercihleri, araştırma notları, doğrulanmış eksik sayıları, tam okunabilen oran dağılımları ve kategori etiketleri de paylaşılır. Ham satırlar ve serbest hücre çıktıları gönderilmez. Yalnız mesaj ve kod seçeneği bu özetleri paylaşmaz. Bu seçim diğer mentor yollarının veri politikasını değiştirmez.",
      summaries: "Mesajım, kodum ve kontrol özetleriyle yardım",
      summariesShared: "Notebook öğretimi mesajlarını, kodunu ve izin verdiğin kontrol özetlerini kullanabilir.",
      generic: "Genel kavramlarla yardım", detailed: "Mesajım ve inceleme kodumla yardım",
      save: "Seçimi kaydet", saving: "Kaydediliyor…", label: "Notebook öğretim bağlamı",
    },
    en: {
      title: "Detailed notebook help",
      limited: "Notebook teaching is in general mode: This teaching path does not send your full question to the model, so detailed code questions may not be answered adequately.",
      shared: "Notebook teaching can use your messages and latest code attempt; a failed attempt is not a completed operation.",
      protected: "This data classification blocks external AI context sharing in this teaching path.",
      description: "Detailed help sends your messages, relevant column names and the latest code attempt (including failed attempts) to the external AI provider. Other code literals and comments are redacted; a local syntax diagnostic and recorded error type may be shared. Values written in messages or code may also be shared. Choosing inspection summaries also shares the project goal, learning preferences, investigation notes, verified missing counts, fully parsed proportion distributions and category labels. Raw rows and free-form cell outputs are not sent. The messages and code option does not share these summaries. This choice does not change data policies for other mentor paths.",
      summaries: "Help using messages, code and inspection summaries",
      summariesShared: "Notebook teaching can use your messages, code and permitted inspection summaries.",
      generic: "Help with general concepts", detailed: "Help using my messages and inspection code",
      save: "Save choice", saving: "Saving…", label: "Notebook teaching context",
    },
    nl: {
      title: "Gedetailleerde notebookhulp",
      limited: "Algemene notebookuitleg: dit uitlegpad stuurt je volledige vraag niet naar het model. Gedetailleerde codevragen worden daardoor mogelijk onvoldoende beantwoord.",
      shared: "Notebookuitleg kan je berichten en laatste codepoging gebruiken; een mislukte poging is geen voltooide bewerking.",
      protected: "Deze gegevensclassificatie blokkeert externe AI-context in dit uitlegpad.",
      description: "Gedetailleerde hulp stuurt je berichten, relevante kolomnamen en de laatste codepoging (ook mislukte pogingen) naar de externe AI-aanbieder. Andere vaste waarden en commentaar worden afgeschermd; een lokale syntaxdiagnose en vastgelegd fouttype kunnen worden gedeeld. Waarden in berichten of code kunnen ook worden gedeeld. Met controleoverzichten deel je ook het projectdoel, leervoorkeuren, onderzoeksnotities, gecontroleerde aantallen ontbrekende waarden, volledig gelezen verhoudingen en categorielabels. Ruwe rijen en vrije celuitvoer worden niet verstuurd. Alleen berichten en code deelt deze overzichten niet. Deze keuze verandert het gegevensbeleid voor andere mentorpaden niet.",
      summaries: "Hulp met berichten, code en controleoverzichten",
      summariesShared: "Notebookuitleg kan je berichten, code en toegestane controleoverzichten gebruiken.",
      generic: "Hulp met algemene begrippen", detailed: "Hulp met mijn berichten en onderzoekscode",
      save: "Keuze opslaan", saving: "Opslaan…", label: "Context voor notebookuitleg",
    },
  }[language];
  const endRef=useRef<HTMLDivElement|null>(null);

  useEffect(() => {
    setTeachingDraft(effectiveTeachingContext);
    setTeachingError(null);
  }, [workspaceId, effectiveTeachingContext]);

  async function saveTeachingContext() {
    if (!onTeachingContextChange || teachingSaving || loading) return;
    setTeachingSaving(true);
    setTeachingError(null);
    try { await onTeachingContextChange(teachingDraft); }
    catch (error) { setTeachingError(error instanceof Error ? error.message : "Preference could not be saved."); }
    finally { setTeachingSaving(false); }
  }

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
      setActiveMode("chat");
      onOpenChange(true);
      setInput(contextualPrompt);
    }
  },[contextualPrompt,contextualPromptKey,onOpenChange]);

  useEffect(()=>{
    if(learningLoopFindingIndex===null) return;

    let cancelled=false;
    setLearningLoopLoading(true);
    setActiveMode("learning");
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

        const persistedHistory = Array.isArray(
          nextLoop.message_history
        )
          ? nextLoop.message_history.filter(
              (item): item is MentorMessage =>
                (
                  item?.role === "user" ||
                  item?.role === "assistant"
                ) &&
                typeof item?.content === "string"
            )
          : [];

        setLearningMessages(
          persistedHistory.length > 0
            ? persistedHistory
            : (
                prompt
                  ? [
                      {
                        role:"assistant",
                        content:prompt,
                      } as MentorMessage,
                    ]
                  : []
              )
        );
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

  async function restartLearningLoop(){
    if(!learningLoop || learningLoopLoading) return;

    setLearningLoopLoading(true);

    try{
      const response=await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/findings/${learningLoop.finding_index}/learning-loop/restart?language=${language}`,
        { method:"POST" }
      );

      const data=await response.json();

      if(!response.ok){
        throw new Error(
          data.detail ||
          "Learning loop could not be restarted."
        );
      }

      const nextLoop =
        data.loop as WorkspaceLearningLoop;

      setLearningLoop(nextLoop);
      setLearningMessages(
        Array.isArray(nextLoop.message_history)
          ? nextLoop.message_history
          : []
      );
      setInput("");
    }catch(error){
      setLearningMessages(prev=>[
        ...prev,
        {
          role:"assistant",
          content:error instanceof Error
            ? error.message
            : "Learning loop could not be restarted.",
        },
      ]);
    }finally{
      setLearningLoopLoading(false);
    }
  }


  async function submit(event?:FormEvent){
    event?.preventDefault();
    const message=input.trim();
    if(!message || !sessionId || loading || teachingSaving) return;

    const structuredPhase =
      activeMode==="learning" &&
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
            body:JSON.stringify({
              response:message,
              ui_context:uiContext ?? null,
              learning_history:
                learningMessages.slice(-6),
            }),
          }
        );

        const data=await response.json();

        if(!response.ok){
          throw new Error(
            data.detail ||
            "Learning response could not be reviewed."
          );
        }

        const nextLoop =
          data.loop as WorkspaceLearningLoop;

        setLearningLoop(nextLoop);

        setLearningMessages(
          Array.isArray(nextLoop.message_history)
            ? nextLoop.message_history
            : []
        );
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
      <div className="workspace-mentor-modes" role="tablist" aria-label="Mentor mode">
        <button
          type="button"
          role="tab"
          aria-selected={activeMode==="chat"}
          className={activeMode==="chat" ? "active" : ""}
          onClick={()=>setActiveMode("chat")}
        >
          {copy.chatMode}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeMode==="learning"}
          className={activeMode==="learning" ? "active" : ""}
          onClick={()=>setActiveMode("learning")}
        >
          {copy.learningMode}
        </button>
      </div>

      {activeMode==="chat" && usageContext==="personal" && onTeachingContextChange && (
        <div className="mentor-teaching-preference">
          <p role="status">{protectedData ? teachingCopy.protected : effectiveTeachingContext === "generic" ? teachingCopy.limited : effectiveTeachingContext === "question_code_and_summaries" ? teachingCopy.summariesShared : teachingCopy.shared}</p>
          {!protectedData && <details>
            <summary>{teachingCopy.title}</summary>
            <p>{teachingCopy.description}</p>
            <label htmlFor="notebook-teaching-context">{teachingCopy.label}</label>
            <select id="notebook-teaching-context" value={teachingDraft} disabled={teachingSaving || loading}
              onChange={event => setTeachingDraft(event.target.value as "generic" | "question_and_code" | "question_code_and_summaries")}>
              <option value="generic">{teachingCopy.generic}</option>
              <option value="question_and_code">{teachingCopy.detailed}</option>
              <option value="question_code_and_summaries">{teachingCopy.summaries}</option>
            </select>
            <button type="button" disabled={teachingSaving || loading || teachingDraft === effectiveTeachingContext}
              onClick={() => { void saveTeachingContext(); }}>{teachingSaving ? teachingCopy.saving : teachingCopy.save}</button>
          </details>}
          {teachingError && <p role="alert">{teachingError}</p>}
        </div>
      )}

      {activeMode==="learning" && learningLoop && (
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
          <button
            type="button"
            className="mentor-learning-restart"
            onClick={()=>{ void restartLearningLoop(); }}
            disabled={learningLoopLoading}
          >
            {copy.restart}
          </button>
        </div>
      )}

      <div className="workspace-mentor-messages">
        {activeMode==="chat" && messages.length===0 && (
          <div className="workspace-mentor-empty"><Sparkles size={18}/><p>{copy.empty}</p></div>
        )}
        {activeMode==="learning" && learningMessages.length===0 && (
          <div className="workspace-mentor-empty"><Sparkles size={18}/><p>{copy.learningEmpty}</p></div>
        )}
        {activeMode==="chat" && messages.map((m,i)=><div key={`chat-${i}`} className={`workspace-mentor-message ${m.role}`}><span>{m.content}</span></div>)}
        {activeMode==="learning" && learningMessages.map((m,i)=><div key={`learning-${i}`} className={`workspace-mentor-message ${m.role} learning`}><span>{m.content}</span></div>)}
        {activeMode==="learning" && learningLoop && learningLoop.status==="active" && (learningLoop.current_phase==="implement" || learningLoop.current_phase==="validate") && (
          <div className="mentor-learning-gate">{copy.workbenchGate}</div>
        )}
        {activeMode==="chat" && loading && <div className="workspace-mentor-message assistant"><span>{copy.thinking}</span></div>}
        {activeMode==="learning" && (loading || learningLoopLoading) && <div className="workspace-mentor-message assistant learning"><span>{learningLoopLoading?copy.learningLoopLoading:copy.thinking}</span></div>}
        <div ref={endRef}/>
      </div>
      <form className="workspace-mentor-composer" onSubmit={submit}>
        <textarea
          value={input}
          onChange={e=>setInput(e.target.value)}
          placeholder={activeMode==="learning" ? copy.learningPlaceholder : copy.placeholder}
          rows={2}
          disabled={
            activeMode==="learning" &&
            (
              !learningLoop ||
              learningLoop.status==="completed" ||
              learningLoop.current_phase==="implement" ||
              learningLoop.current_phase==="validate"
            )
          }
          onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();void submit();}}}
        />
        <button
          type="submit"
          disabled={
            !input.trim() ||
            loading ||
            teachingSaving ||
            (
              activeMode==="learning" &&
              (
                !learningLoop ||
                learningLoop.status==="completed" ||
                learningLoop.current_phase==="implement" ||
                learningLoop.current_phase==="validate"
              )
            )
          }
          title={copy.send}
        >
          <Send size={17}/>
        </button>
      </form>
    </>
  </aside>;
}
