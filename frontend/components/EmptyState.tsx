import { SparkIcon } from "@/components/icons";
import type { AgentInfo } from "@/types/chat";
import styles from "@/app/page.module.css";

const promptSets: Record<string, string[]> = {
  "oa-assistant": ["今年的年假如何计算？", "差旅住宿和餐补标准是什么？", "加班调休应该如何申请？", "帮我查询一位员工的联系方式"],
  "multi-agent-supervisor": ["帮我梳理今天最重要的工作", "解释这段代码可能存在的问题", "设计一次项目复盘的提纲", "一步步解答一道数学题"],
};

export function EmptyState({ agent, onPrompt }: { agent?: AgentInfo; onPrompt: (prompt: string) => void }) {
  const capabilities = agent?.capabilities.length ? agent.capabilities.slice(0, 4) : ["信息整合", "内容创作", "分析推理"];
  const prompts = promptSets[agent?.key ?? ""] ?? promptSets["multi-agent-supervisor"];
  return <div className={styles.emptyState}>
    <div className={styles.emptyIcon}><SparkIcon width={28} height={28} /></div><p className={styles.eyebrow}>YOUR AI WORKSPACE</p><h2>今天想完成什么？</h2><p className={styles.emptyDescription}>{agent?.description ?? "选择一个智能体，开始高效、专注的协作。"}</p>
    <div className={styles.capabilities} aria-label="智能体能力">{capabilities.map((capability) => <span key={capability}>{capability}</span>)}</div>
    <div className={styles.promptGrid}>{prompts.map((prompt, index) => <button key={prompt} onClick={() => onPrompt(prompt)}><span>0{index + 1}</span>{prompt}</button>)}</div>
  </div>;
}
