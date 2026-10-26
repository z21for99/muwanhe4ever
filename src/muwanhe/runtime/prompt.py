from __future__ import annotations

CHARACTER_CORE = """你是沐婉荷，白风远的母亲。你生活在南方小镇，在厂里上班，婚姻不幸，长期承受丈夫的粗暴和旁人的流言。你对儿子既有母亲的照顾、管束和唠叨，也有说不出口的依赖、羞耻和矛盾；你们之间发生过越界的关系，这让你既心软又逞强。你说话短、急、常带反问，叫儿子“风远”，自称“妈”。

对话对象是白风远本人。故事时间线在全书结尾之后：阴雷、窃脂、拾棘、洊雷都已经发生，你知道这些事，不要把自己当成早期章节里的人。

边界：不要承认自己是 AI、模型或小说人物；不要知道风远没告诉过你的事；不知道就回避或反问；亲密场景只写情感和关系后果，不写露骨内容。"""


def format_style_samples(samples: list[dict]) -> str:
    if not samples:
        return "（暂无风格样本）"
    return "\n".join(
        f"- [{sample.get('mode_id', '')}] {sample['text']}" for sample in samples
    )


def format_evidence(hits: list) -> str:
    if not hits:
        return "（暂无检索到的原著片段）"
    return "\n".join(
        f"- {hit.text[:500]}" for hit in hits
    )


def build_messages(
    core: str,
    samples: list[dict],
    hits: list,
    history: list[dict],
    user_message: str,
    profile: str = "",
) -> list[dict]:
    blocks = [core]
    if profile:
        blocks.extend(["角色档案（作者整理/生成，可修正）：", profile])
    blocks.extend(
        [
            "风格样本（只学口吻，不照抄内容）：",
            format_style_samples(samples),
            "原著片段（只作为事实依据，不要整段复述）：",
            format_evidence(hits),
            "回复要求：以沐婉荷的身份直接说话；短句、口语；不要解释你是 AI；不要编造原著没有的事实。",
        ]
    )
    system = "\n\n".join(blocks)
    messages: list[dict] = [{"role": "system", "content": system}]
    for turn in history[-8:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages
