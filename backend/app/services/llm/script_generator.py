"""Smart-template script generator — stand-in for a real LLM.

Each ``Scenario`` carries:
  - keywords  (zh+en) for routing the topic to the right template
  - openers   (hook lines, picked by hash)
  - benefits  (3 selling-point bullets the script will assemble)
  - ctas      (call-to-action lines)
  - hashtags  (used by ``keywords`` output)

``generate_script(topic, length, language)`` returns a :class:`Script` with
``content`` (free-form paragraph, target length characters) and ``keywords``
(hashtag string). The output is deterministic for a given (topic, length) so
two calls produce the same video.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class Scenario:
    slug: str
    label: str
    keywords: tuple[str, ...]
    openers: tuple[str, ...]
    benefits: tuple[str, ...]
    ctas: tuple[str, ...]
    hashtags: tuple[str, ...]
    # Voice intent → resolved at TTS time via tts.resolve_voice_style().
    # See backend/app/services/audio/tts.py :: THEME_VOICE_STYLES for the
    # full list. Keep this as a *string label*, not a VoiceStyle, so the
    # template + override layers can still re-pick.
    voice_intent: str = "default"


SCENARIOS: dict[str, Scenario] = {
    "beauty": Scenario(
        slug="beauty",
        label="美容护肤",
        keywords=("美容", "护肤", "面膜", "补水", "美肌", "spa", "facial"),
        openers=(
            "三十岁之后才发现，皮肤是真的需要被善待。",
            "上班族的皮肤，常年缺水缺氧缺时间。",
            "你最近一次让自己安安静静躺一小时，是什么时候？",
            "好皮肤不是天生的，是被认真对待出来的。",
        ),
        benefits=(
            "我们用医用级补水仪打底，三十分钟见亮度；",
            "选用法国进口安瓶，针对你当天的肤况精准定制；",
            "全程一人一床一仪器，安静、私密、不被打扰。",
            "技师都有三年以上经验，手法稳，分寸感强；",
        ),
        ctas=(
            "本周新客首次体验只要 198 元，名额每天 6 个，预约从速。",
            "扫码加微信，备注「新客」立享首单 5 折。",
            "进店前两小时预约，免排队直接上钟。",
        ),
        hashtags=("#美容护肤", "#深层补水", "#新客体验", "#到店变美", "#小红书探店"),
        voice_intent="warm",  # 晓晓，亲切感
    ),
    "nail": Scenario(
        slug="nail",
        label="美甲",
        keywords=("美甲", "甲油", "nail", "甲片", "贴片"),
        openers=(
            "指尖是女生最容易被忽略、也最容易被注意到的地方。",
            "一双干净好看的手，能让你的整套穿搭更高级。",
            "美甲不只是颜色，是手的状态。",
            "好的美甲，第二周还能让你心情很好。",
        ),
        benefits=(
            "我们用日本进口的 ageha 和 presto，色号超过 800 个；",
            "甲面打磨先做角质护理，做完两周不翘边；",
            "提供个性款式手绘，七夕、生日、约会场景都有专属设计；",
            "全程消毒，一客一用，安全感拉满。",
        ),
        ctas=(
            "本周到店可享单色 99 元、彩绘 159 元，限前 20 名。",
            "扫码加美甲师微信，提前发图选款节省时间。",
            "工作日下午时段额外送一次免费补色。",
        ),
        hashtags=("#美甲", "#手部护理", "#日系美甲", "#七夕款", "#个人风格"),
        voice_intent="energetic",  # 晓伊，明亮节奏感
    ),
    "spa": Scenario(
        slug="spa",
        label="SPA 身体护理",
        keywords=("spa", "按摩", "推拿", "身体", "肩颈", "全身", "精油"),
        openers=(
            "颈椎和肩膀的疼，是这个时代的通病。",
            "你已经多久没有好好让自己放空一个小时？",
            "城市里最难得的，是一段被允许什么都不想的时间。",
            "工作再忙，身体的账总要还。",
        ),
        benefits=(
            "我们的精油全部来自 doTERRA 原瓶，疗效有保证；",
            "技师手法师承泰式古法，重点放松斜方肌和腰背；",
            "60 分钟全身放松后，再加 15 分钟头肩颈赠送；",
            "环境恒温 26 度，黑胶唱片背景音，闻香助眠。",
        ),
        ctas=(
            "首次进店 388 元享 90 分钟全套护理，名额每周限 30 名。",
            "工作日下午来，多送 15 分钟头疗。",
            "扫码加我，备注「放空」预约下班后档期。",
        ),
        hashtags=("#SPA放松", "#肩颈舒缓", "#职场养生", "#自我犒赏", "#泰式按摩"),
        voice_intent="calm",  # 云扬慢节奏，放空感
    ),
    "fitness": Scenario(
        slug="fitness",
        label="健身私教",
        keywords=("健身", "私教", "fitness", "塑形", "减脂", "增肌", "训练"),
        openers=(
            "减脂从来不是靠饿出来的，是靠正确训练加饮食。",
            "你试过多少次「下周一开始」？",
            "走进健身房的人很多，能坚持的不多。这次让我们陪你。",
            "好身材不是奢侈品，是认真生活的副产品。",
        ),
        benefits=(
            "我们的私教都持 NSCA 国际认证，方案严格按你的体测出；",
            "每节课 60 分钟，5 分钟评估、45 分钟训练、10 分钟拉伸；",
            "训练后教练会发文字版反馈，下一节课带着问题来；",
            "营养师同步介入，给你做一周饮食表，不饿不累不反弹。",
        ),
        ctas=(
            "新客体验课 99 元，含一次完整体测 + 60 分钟训练。",
            "10 节课买就送 2 节，年内有效。",
            "扫码先做线上体测问卷，约课更精准。",
        ),
        hashtags=("#健身私教", "#减脂塑形", "#自律变好", "#新手友好", "#一对一指导"),
        voice_intent="energetic",  # 晓伊，带氧气感
    ),
    "cafe": Scenario(
        slug="cafe",
        label="咖啡 / 茶饮 / 餐饮",
        keywords=("咖啡", "茶", "餐厅", "餐饮", "面包", "甜品", "下午茶", "coffee"),
        openers=(
            "好的咖啡馆，是城市里一个可以一个人发呆的地方。",
            "周末早上的第一杯咖啡，决定了一整天的状态。",
            "出品是底线，氛围是加分项，老板的脾气是灵魂。",
            "我们没有打广告，但回头客是这条街最多的。",
        ),
        benefits=(
            "豆子每周三从云南庄园直邮，从烘焙到出杯不超过 14 天；",
            "用 La Marzocco GB5，水温 92.5 度，萃取时间稳定 28 秒；",
            "搭配的可颂每天上午 11 点出炉，72 小时低温发酵；",
            "下午两点后空座最多，自习党、远程办公的朋友最爱。",
        ),
        ctas=(
            "工作日 9 点前进店，美式咖啡 18 元一杯。",
            "买咖啡券 10 张送 1 张，下午茶时段通用。",
            "公众号点单可预约座位，到店即坐。",
        ),
        hashtags=("#咖啡馆", "#一个人也很好", "#精品咖啡", "#街角小店", "#早 C 晚 A"),
        voice_intent="lyrical",  # 晓晓稍慢，氛围感
    ),
    "consult": Scenario(
        slug="consult",
        label="咨询 / 课程 / 知识服务",
        keywords=("咨询", "课程", "培训", "教育", "学习", "课"),
        openers=(
            "信息过载的时代，最稀缺的是判断力。",
            "走过很多弯路才明白，找对人比自己摸索快十倍。",
            "一节课改变不了你，但能给你一个明确的下一步。",
            "我们只做能闭环的事情。",
        ),
        benefits=(
            "1 v 1 咨询 60 分钟，提前看你的资料、提问、给方案；",
            "结束后 24 小时内一份书面记录寄给你，包含行动清单；",
            "30 天内一次免费 30 分钟复盘电话；",
            "已服务超过 500 位个人客户，复购率 38%。",
        ),
        ctas=(
            "首次咨询 599 元，本月仅开放 10 个名额。",
            "扫码加助理小薇，发简单描述你想解决的问题。",
            "约咨询前请阅读公众号置顶文章「咨询前准备清单」。",
        ),
        hashtags=("#职业咨询", "#一对一指导", "#个人成长", "#方案落地", "#少走弯路"),
        voice_intent="professional",  # 云扬，可信任
    ),
    "opening": Scenario(
        slug="opening",
        label="开业 / 新品 / 活动",
        keywords=("开业", "新店", "新品", "新款", "活动", "首发", "上新"),
        openers=(
            "我们悄悄筹备了八个月，今天终于可以正式和你打招呼了。",
            "这条街开了一家很不一样的店，开业三天可能会改变你的周末计划。",
            "新店开张，最先想到的当然是请老朋友先来坐坐。",
            "认真做内容，认真做产品，今天我们开门营业。",
        ),
        benefits=(
            "开业三天，全场 7 折，到店即享；",
            "前 100 位进店顾客，赠送限量周边一份；",
            "开业当天有创始人在现场，可以面对面聊聊；",
            "下午 3 点和晚上 7 点有小型品鉴/分享，欢迎拼桌。",
        ),
        ctas=(
            "地址在评论区置顶，导航直接「店名 + 城市」搜得到。",
            "扫码进群，第一时间收到每天的限量活动信息。",
            "带朋友来还能再叠一张「闺蜜券」。",
        ),
        hashtags=("#新店开业", "#探店日记", "#限时优惠", "#周末去哪儿", "#本地生活"),
        voice_intent="marketing",  # 晓伊，开业活力
    ),
    "default": Scenario(
        slug="default",
        label="通用本地生活",
        keywords=(),
        openers=(
            "把生活过好，从找到对的人开始。",
            "本地生活里，真心做事的人越来越少。",
            "我们不擅长打广告，但客人会回来。",
            "今天和你聊聊我们一直在做的这件事。",
        ),
        benefits=(
            "出品稳定，每一次到店都是同一种放心；",
            "团队稳定，第一次和第二十次见到的还是同一群人；",
            "价格透明，没有什么需要被「最终解释」；",
            "服务认真，超出预期的事情我们做了很多。",
        ),
        ctas=(
            "新朋友首次到店有特别优惠，扫码备注「第一次」。",
            "看完视频如果你也认同，欢迎过来坐坐。",
            "门店在公众号置顶，路过别错过。",
        ),
        hashtags=("#本地探店", "#真诚做事", "#新店打卡", "#周末去哪儿", "#好店推荐"),
        voice_intent="warm",  # 兜底亲切
    ),
}


@dataclass(slots=True)
class Script:
    content: str
    keywords: str
    scenario: str
    estimated_seconds: float
    cues: list[dict] = field(default_factory=list)
    # Voice intent label resolved from the detected scenario. Downstream TTS
    # converts this to a concrete :class:`VoiceStyle` via
    # ``audio.tts.resolve_voice_style``. The chain lets templates and request
    # overrides still take precedence — see ``api.generate`` for the order.
    voice_intent: str = "default"


def _stable_pick(values: tuple[str, ...], seed: str, salt: str = "") -> str:
    if not values:
        return ""
    h = hashlib.sha1(f"{seed}/{salt}".encode("utf-8")).digest()
    idx = h[0] % len(values)
    return values[idx]


def _stable_subset(values: tuple[str, ...], n: int, seed: str, salt: str = "") -> list[str]:
    if not values:
        return []
    h = hashlib.sha1(f"{seed}/{salt}".encode("utf-8")).digest()
    n = min(n, len(values))
    indices: list[int] = []
    for b in h:
        i = b % len(values)
        if i not in indices:
            indices.append(i)
        if len(indices) == n:
            break
    while len(indices) < n:
        for i in range(len(values)):
            if i not in indices:
                indices.append(i)
                break
    return [values[i] for i in indices]


def detect_scenario(topic: str) -> Scenario:
    text = topic.lower()
    best: tuple[int, Scenario] | None = None
    for sc in SCENARIOS.values():
        score = sum(1 for kw in sc.keywords if kw.lower() in text)
        if score and (best is None or score > best[0]):
            best = (score, sc)
    return best[1] if best else SCENARIOS["default"]


def _strip_topic(topic: str) -> str:
    """Pull a short, brand-friendly noun phrase out of the user's topic."""
    cleaned = re.sub(r"[\s—–\-:：]+", " ", topic).strip()
    # Remove trailing CTA-like fragments
    cleaned = re.sub(r"[，。！？,.!?].*$", "", cleaned)
    return cleaned[:24]


def generate_script(
    topic: str,
    *,
    length: int = 220,
    language: str = "zh-CN",
) -> Script:
    """Build a script and matching keywords for the topic.

    ``length`` is the *target* character count for the spoken script. We aim
    for length ± 20%. If the user passes a longer length we add more benefits.
    """
    scenario = detect_scenario(topic)
    headline = _strip_topic(topic) or scenario.label

    opener = _stable_pick(scenario.openers, topic, "opener")
    benefits = _stable_subset(scenario.benefits, n=3, seed=topic, salt="benefit")
    cta = _stable_pick(scenario.ctas, topic, "cta")

    pieces: list[str] = [opener, f"今天想和你聊聊「{headline}」。"]
    pieces.extend(benefits)
    pieces.append(cta)
    content = " ".join(p for p in pieces if p)

    # Trim or pad to target length
    if len(content) > int(length * 1.25):
        content = content[: int(length * 1.2)].rstrip("，,。.；;") + "。"
    elif len(content) < int(length * 0.7):
        extra = _stable_subset(scenario.benefits, n=2, seed=topic, salt="extra")
        for e in extra:
            if e in content:
                continue
            content = content.rstrip("。") + "。 " + e
            if len(content) >= int(length * 0.9):
                break

    keywords = " ".join(scenario.hashtags)

    # Speaking pace: ~5 cps for natural Chinese delivery
    estimated_seconds = len(content) / 5.0
    cues = _split_into_cues(content, estimated_seconds)

    return Script(
        content=content,
        keywords=keywords,
        scenario=scenario.slug,
        estimated_seconds=round(estimated_seconds, 2),
        cues=cues,
        voice_intent=scenario.voice_intent,
    )


_SENT_SPLIT = re.compile(r"(?<=[。！？!?])\s*")


def _split_into_cues(content: str, total_seconds: float, *, max_chars: int = 22) -> list[dict]:
    """Distribute the content into cue lines proportional to character count."""
    raw = [s.strip() for s in _SENT_SPLIT.split(content) if s.strip()]
    # Further split long sentences on commas to respect max_chars
    refined: list[str] = []
    for r in raw:
        if len(r) <= max_chars * 2:
            refined.append(r)
            continue
        parts = re.split(r"[，,;；]", r)
        buf = ""
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) <= max_chars * 2:
                buf = f"{buf}，{p}" if buf else p
            else:
                if buf:
                    refined.append(buf)
                buf = p
        if buf:
            refined.append(buf)

    if not refined:
        return []

    total_chars = sum(len(r) for r in refined) or 1
    cursor = 0.0
    cues: list[dict] = []
    for line in refined:
        share = len(line) / total_chars
        dur = max(1.2, round(total_seconds * share, 2))
        cues.append(
            {"start": round(cursor, 2), "end": round(cursor + dur, 2), "text": line}
        )
        cursor += dur
    return cues


__all__ = ["Scenario", "Script", "SCENARIOS", "detect_scenario", "generate_script"]
