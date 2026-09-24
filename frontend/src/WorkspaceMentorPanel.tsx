import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { BrainCircuit, Send, Sparkles, X } from "lucide-react";

type MentorMessage = { role: "user" | "assistant"; content: string };

type Props = {
  workspaceId: string;
  sessionId: string | null;
  language: "en" | "nl" | "tr";
  contextualPrompt?: string | null;
  contextualPromptKey?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export default function WorkspaceMentorPanel({
  workspaceId, sessionId, language, contextualPrompt, contextualPromptKey, open, onOpenChange,
}: Props) {
  const copy = {
    en: { title:"DataPilot Mentor", subtitle:"Workspace-aware senior mentor", placeholder:"Ask about your current work...", send:"Send", empty:"I follow this workspace, its data-quality findings, notebook and pipeline. Ask me what to investigate or do next.", close:"Close", collapse:"Collapse", expand:"Open mentor", thinking:"Thinking..." },
    nl: { title:"DataPilot Mentor", subtitle:"Senior mentor met werkruimtecontext", placeholder:"Vraag iets over je huidige werk...", send:"Versturen", empty:"Ik volg deze werkruimte, de datakwaliteitsbevindingen, het notebook en de pipeline. Vraag wat je nu moet onderzoeken of doen.", close:"Sluiten", collapse:"Inklappen", expand:"Mentor openen", thinking:"Nadenken..." },
    tr: { title:"DataPilot Mentor", subtitle:"Çalışma alanını bilen kıdemli mentor", placeholder:"Mevcut çalışman hakkında sor...", send:"Gönder", empty:"Bu çalışma alanını, veri kalitesi bulgularını, notebook'u ve pipeline'ı takip ediyorum. Şimdi neyi incelemen veya yapman gerektiğini sorabilirsin.", close:"Kapat", collapse:"Daralt", expand:"Mentoru aç", thinking:"Düşünüyor..." },
  }[language];

  const [messages,setMessages]=useState<MentorMessage[]>([]);
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

  useEffect(()=>{ endRef.current?.scrollIntoView({behavior:"smooth"}); },[messages,loading]);

  async function submit(event?:FormEvent){
    event?.preventDefault();
    const message=input.trim();
    if(!message || !sessionId || loading) return;
    setInput(""); setLoading(true);
    setMessages(prev=>[...prev,{role:"user",content:message}]);
    try{
      const response=await fetch("http://127.0.0.1:8000/chat",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({session_id:sessionId,learner_id:"demo-learner",workspace_id:workspaceId,message}),
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
      <div className="workspace-mentor-messages">
        {messages.length===0 && <div className="workspace-mentor-empty"><Sparkles size={18}/><p>{copy.empty}</p></div>}
        {messages.map((m,i)=><div key={i} className={`workspace-mentor-message ${m.role}`}><span>{m.content}</span></div>)}
        {loading && <div className="workspace-mentor-message assistant"><span>{copy.thinking}</span></div>}
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
