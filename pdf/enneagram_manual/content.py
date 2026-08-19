"""The copy bank: nine archetypes, five relationship lenses, and the rules
that let them be combined without contradicting each other.

Two design decisions worth knowing before you edit anything here.

**Pronouns.** Every line is written with singular *they/them/their* and
plural verb agreement, with the person referred to as ``{subject}``. This is
not a style preference -- it removes an entire class of template bug
(``"she need"`` / ``"they needs"``) and means a buyer who tests their mom,
their boyfriend, or a best friend of unknown gender all get grammatical
copy from the same string. Do not add pronoun variables.

**Blending.** There are 72 possible core+secondary pairings and 45
type/relationship combinations. None of them are hand-authored. Each
archetype declares what it contributes *as a core* and what flavour it adds
*as a secondary*; :mod:`.blending` composes those, and where two archetypes
genuinely pull in opposite directions (``CLAIM_CONFLICTS``) it says so
explicitly rather than printing both claims as though they agree. That is
why the output reads as one voice instead of two stapled together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .errors import ContentError

# --------------------------------------------------------------------------
# Vocabulary available to every template in this file.
# templating.audit_templates() checks the whole bank against this set at
# import time, so a typo here fails the build, never a buyer's download.
# --------------------------------------------------------------------------

VOCABULARY: set[str] = {
    "subject",            # "your mom" or the name they typed
    "subject_poss",       # "your mom's" / "Dana's"
    "relation",           # "mom"
    "relation_label",     # "Mom"
    "core_name", "core_title",
    "secondary_name", "secondary_title",
    "wing_name",
    "core_pull", "secondary_pull",   # used by TENSION_TEMPLATES
    "core_bare", "secondary_bare", "wing_bare",   # name without the leading "The"
    "core_pct", "secondary_pct",
    "question_count",
    "channel",            # how this relationship actually communicates
    "stakes",             # why this relationship raises the cost
    "ask_form",           # the shape a request should take here
    "repair_window",      # how long you have before damage sets
}


# --------------------------------------------------------------------------
# Claim tags -- the contradiction guard
# --------------------------------------------------------------------------
#
# Each archetype declares the behavioural claims its copy makes. When two
# archetypes are blended, any pair listed here is *incompatible*: printing
# both would tell the buyer two opposite things about the same person on
# facing pages. The blender detects the collision and swaps in a tension
# line that names the push-pull instead.

CLAIM_CONFLICTS: frozenset[frozenset[str]] = frozenset({
    frozenset({"avoids-conflict", "seeks-conflict"}),
    frozenset({"needs-space", "needs-contact"}),
    frozenset({"over-discloses", "withholds"}),
    frozenset({"image-managed", "raw-honest"}),
    frozenset({"future-focused", "past-anchored"}),
    frozenset({"decisive", "deliberating"}),
    frozenset({"self-erasing", "self-asserting"}),
})

TENSION_TEMPLATES: tuple[str, ...] = (
    "This is the part most people miss about {subject}: the {core_bare} in them wants "
    "{core_pull}, and the {secondary_bare} underneath wants {secondary_pull}. Those two "
    "do not resolve. They alternate. What looks like inconsistency is one person losing "
    "an argument with themselves in real time.",
    "You are dealing with a genuine internal split. {core_pull} is the {core_bare} "
    "instinct; {secondary_pull} is the {secondary_bare} one. {subject} does not choose "
    "between them so much as swing, and which one you get depends almost entirely on how "
    "safe the last ten minutes felt.",
    "Hold both of these at once or nothing about {subject} will make sense: they want "
    "{core_pull}, and they also want {secondary_pull}. When you push on one, the other "
    "surfaces — which is why the same request can land beautifully one week and land as "
    "an attack the next.",
)


@dataclass(frozen=True)
class Trigger:
    """One reliable detonation point, and what to do with the pin."""

    name: str
    looks_like: str     # what you observe
    why: str            # what is actually happening underneath
    instead: str        # the substitution


@dataclass(frozen=True)
class CheatSheet:
    """The page they screenshot. Every line has to survive without context."""

    say: str
    never_say: str
    when_quiet: str
    when_angry: str
    green_flag: str
    red_flag: str
    one_sentence: str   # the sentence that ends most of your fights


@dataclass(frozen=True)
class Archetype:
    """One of the nine. Every field is required -- see validate_content()."""

    type_id: int
    name: str
    title: str
    glyph: str
    one_line: str

    core_fear: str
    core_desire: str
    core_lie: str
    world_view: str

    gift: str
    friction: str

    stress_to: int
    stress_text: str
    growth_to: int
    growth_text: str

    tells: tuple[str, ...]
    triggers: tuple[Trigger, ...]

    deescalation: tuple[str, ...]
    repair: str
    repair_scripts: tuple[str, ...]
    boundary_scripts: tuple[str, ...]
    apology_to_them: str
    their_apology: str

    safe: tuple[str, ...]
    never: tuple[str, ...]
    starters: tuple[str, ...]
    hard_conversation: tuple[str, ...]

    daily_rhythm: str
    #: The archetype this one is most often mistaken for, and the tell that
    #: separates them. This is the single most common mis-read, so it earns
    #: its place early in the manual.
    mistaken_for: str
    cheat: CheatSheet

    #: What this type contributes when it is the SECONDARY of another type.
    as_secondary: str
    #: The short noun phrase used in tension lines: "to be right".
    pull: str
    claims: frozenset[str]


def _t(name: str, looks_like: str, why: str, instead: str) -> Trigger:
    return Trigger(name=name, looks_like=looks_like, why=why, instead=instead)


# --------------------------------------------------------------------------
# The nine
# --------------------------------------------------------------------------

ARCHETYPES: dict[int, Archetype] = {}


ARCHETYPES[1] = Archetype(
    type_id=1, name="The Perfector", glyph="I",
    title="The one who cannot let it be good enough",
    one_line=(
        "{subject} runs a permanent internal audit, and the loudest auditor is pointed "
        "at themselves. What reaches you is the overflow."
    ),
    core_fear="being fundamentally flawed, and having someone finally notice",
    core_desire="to be beyond reproach — good, correct, and unable to be blamed",
    core_lie="If I hold the standard, I am safe. If I let it slip, I am the problem.",
    world_view=(
        "The world is a place where things are slipping and almost nobody is willing to "
        "hold the line. So they hold it, and resent that they have to."
    ),
    gift=(
        "Absolute reliability. When {subject} says a thing will be handled, it is handled, "
        "at a standard nobody asked for and everybody benefits from. You have almost "
        "certainly never had to check their work."
    ),
    friction=(
        "The standard does not stay on the task. It migrates onto you. Correction arrives "
        "as help, criticism arrives as concern, and you end up defending choices you did "
        "not know were on trial."
    ),
    stress_to=4, stress_text=(
        "Under sustained pressure {subject} stops being crisp and starts being wounded. "
        "The corrections turn inward and personal — nothing is right, they are not right, "
        "nobody appreciates what it costs to hold all this together. If you are hearing "
        "self-pity from someone who is normally all discipline, they are past their limit."
    ),
    growth_to=7, growth_text=(
        "When {subject} feels genuinely unjudged, the grip loosens and something almost "
        "playful comes out. They get funny. They let a plan change without a post-mortem. "
        "This is the version of them you get by removing pressure, never by asking for it."
    ),
    tells=(
        "Reworks something that was already finished",
        "Says fine in a tone that is doing a lot of work",
        "Apologises for the thing they did well",
        "Cannot let a small factual error pass uncorrected",
    ),
    triggers=(
        _t("Being corrected in front of anyone",
           "instant flat tone, over-precise language, a sudden pivot to logistics",
           "public correction confirms the private accusation they already live with — "
           "that they are the flawed one",
           "take the correction sideways and later: never in a group, never in the moment"),
        _t("Carelessness that costs someone else",
           "disproportionate irritation at something small — a missed reply, a late bill",
           "to them the small thing is not small, it is evidence that standards are "
           "optional and they are the only one still paying for them",
           "name the cost before they do: I know that landed on you, and it should not have"),
        _t("Being told to relax",
           "cold silence, or a very controlled list of everything currently unhandled",
           "relax reads as your standards are ridiculous, which is the exact accusation "
           "they most fear is true",
           "offer specific relief instead of a mood instruction: I've got the {relation} "
           "stuff tonight, it does not need to be perfect"),
        _t("An unresolved mess left visible",
           "circling, tidying, tightening — activity that is not really about the mess",
           "a visible mess is an open loop, and open loops read as danger, not clutter",
           "close one loop out loud so the audit can stop: that's done, I finished it"),
        _t("Hypocrisy — yours or anyone's",
           "a very quiet, very final withdrawal of respect",
           "their whole system rests on the belief that holding the line means something; "
           "hypocrisy suggests it does not",
           "own the gap yourself first: I said I'd do it and I didn't. That's on me"),
    ),
    deescalation=(
        "You're right that it matters, and you're right that I let it slide.",
        "I'm not asking you to lower the bar. I'm asking you to let me carry part of it.",
        "You don't have to be the only one holding this.",
    ),
    repair=(
        "{subject} does not need you to grovel; they need the standard acknowledged. A "
        "repair that skips straight to feelings reads as an attempt to dodge the actual "
        "point. Concede the specific thing first, in plain language, without a "
        "counter-grievance attached — then feelings land."
    ),
    repair_scripts=(
        "Here's what I got wrong, specifically: I said I'd handle it and then I didn't, "
        "and you had to pick it up. That's the part I'd be annoyed about too.",
        "I don't think you were being harsh. I think I was being defensive because you "
        "were right.",
    ),
    boundary_scripts=(
        "I want your read on this when I ask for it. When I don't ask, I need you to let "
        "me get it wrong.",
        "I'm not going to do it that way. It's not a rejection of you — it's just mine to "
        "get wrong.",
        "You can tell me once. After that it stops being information and starts being "
        "pressure.",
    ),
    apology_to_them=(
        "Be specific and unhedged. One clean sentence naming exactly what you did, no "
        "because attached. The word because triggers the audit."
    ),
    their_apology=(
        "{subject} apologises by fixing things. A repaired shelf, a rewritten email, a "
        "problem quietly solved before you woke up — that is the apology. Waiting for the "
        "words will cost you years."
    ),
    safe=(
        "Knowing exactly what is expected and by when",
        "Being told they did it right, in specific terms",
        "Order restored before rest",
        "Being trusted with the part that actually matters",
    ),
    never=(
        "Call them uptight, dramatic, or obsessive",
        "Correct their correction in front of other people",
        "Promise something and then renegotiate the terms quietly",
        "Tell them nobody else cares about this",
    ),
    starters=(
        "What's the thing you keep fixing that nobody's ever thanked you for?",
        "If you could let one standard go for a month, which one and what would happen?",
        "What did you get in trouble for as a kid that you now think you were right about?",
    ),
    hard_conversation=(
        "Open by conceding the true part of their position, out loud, first.",
        "State your one thing in a single sentence — no preamble, they will read preamble "
        "as evasion.",
        "Give them the fact base. They can accept an unwelcome fact; they cannot accept a "
        "vibe.",
        "Close with what you will do, not how you feel. Commitments settle them; "
        "reassurance does not.",
    ),
    daily_rhythm=(
        "Front-load the day with certainty and end it with a closed loop. {subject} "
        "operates best when the morning contains no ambiguity about who is doing what, "
        "and the evening contains at least one thing visibly finished."
    ),
    mistaken_for=(
        "People read {subject} as controlling. The difference is where the pressure points: a controlling person wants you to do it their way, and a Perfector wants it done right, including by themselves, especially by themselves. Watch who gets the harshest version — it is almost always them."
    ),
    cheat=CheatSheet(
        say="You were right about that, and I should have listened sooner.",
        never_say="You need to relax.",
        when_quiet="They are re-running the conversation looking for their own error. "
                   "Interrupt it with a specific piece of praise.",
        when_angry="Concede the factual point before addressing the tone. Tone-first "
                   "always escalates with this one.",
        green_flag="They joke about their own standards. That is the relaxed version.",
        red_flag="Self-criticism replacing criticism of the situation — they have "
                 "slid into the stress pattern.",
        one_sentence="I'm not trying to lower the bar — I'm trying to help you carry it.",
    ),
    as_secondary=(
        "a running internal audit that never fully switches off, so even their generous "
        "moments come with a quiet assessment attached"
    ),
    pull="to get it right and be beyond reproach",
    claims=frozenset({"self-asserting", "raw-honest", "deliberating", "past-anchored"}),
)


ARCHETYPES[2] = Archetype(
    type_id=2, name="The Overgiver", glyph="II",
    title="The one who gives until it becomes a debt",
    one_line=(
        "{subject} meets your needs before you have finished having them, and somewhere "
        "in there, an invoice starts running that neither of you agreed to."
    ),
    core_fear="being genuinely unwanted — needed by no one, and therefore disposable",
    core_desire="to be indispensable to the people they love",
    core_lie="If I am necessary, I cannot be left.",
    world_view=(
        "Love is a transaction nobody admits is a transaction. They pay first, "
        "generously, and then wait to see whether anyone pays back."
    ),
    gift=(
        "Being genuinely known. {subject} tracks what you need at a resolution most people "
        "never manage — your bad weeks, your foods, the thing you mentioned once in "
        "March. Being cared for by them is not a metaphor; it is logistics."
    ),
    friction=(
        "The giving is not free, and the price is never quoted. It surfaces later as hurt, "
        "as a list of everything they have done, as a guilt you cannot argue with because "
        "every item on it is true."
    ),
    stress_to=8, stress_text=(
        "When the ledger goes too far out of balance, the warmth flips hard. {subject} "
        "gets blunt, territorial, and startlingly direct about what they are owed. People "
        "who have only seen the giving version find this terrifying. It is not a new "
        "person; it is the bill arriving."
    ),
    growth_to=4, growth_text=(
        "The healthy direction is inward, not outward. When {subject} is safe, they stop "
        "performing usefulness and start saying what they actually want — often haltingly, "
        "because they have very little practice. Protect those moments. They are rare and "
        "easily withdrawn."
    ),
    tells=(
        "Answers a question about themselves with an update about you",
        "Knows the details of your life you have not told them",
        "Says it's fine while quietly keeping score",
        "Gets flustered by a direct question about what they want",
    ),
    triggers=(
        _t("Having help refused",
           "an over-bright it's no trouble, followed by doing it anyway",
           "refusing the help is not refusing a favour, it is refusing the role they use "
           "to stay safe",
           "redirect rather than refuse: I don't need that, but I'd love it if you did "
           "this instead"),
        _t("Watching you go to someone else first",
           "a pointed question about who told you that, delivered lightly",
           "being second is the early warning of being unnecessary, which is the whole fear",
           "close the loop deliberately: I went to them for the logistics — I wanted your "
           "read on the actual decision"),
        _t("The ledger going unacknowledged too long",
           "a sudden inventory of everything they have done, apparently out of nowhere",
           "the list has been accumulating in silence for weeks; you are hearing the total, "
           "not the incident",
           "pay in specifics before the total is due: name one concrete thing they did, "
           "weekly, unprompted"),
        _t("Being told they are too much",
           "immediate over-apology, then a cold, efficient withdrawal of care",
           "too much confirms that the giving — the only currency they trust — is the "
           "problem",
           "separate the act from the person: this is more than I can take right now, and "
           "it is not because it is you"),
        _t("Your independence, on a bad day",
           "unsolicited advice about a thing you have clearly handled",
           "your not needing them reads as a countdown, not as good news",
           "give them a real job. A small genuine need defuses this faster than any "
           "reassurance"),
    ),
    deescalation=(
        "I see how much you carry for me. I'm not taking it for granted.",
        "You don't have to earn this. You already have it.",
        "Tell me what you want. Not what I want — what you want.",
    ),
    repair=(
        "{subject} needs to hear that the relationship survives them being difficult. "
        "Their private fear is that their worth is entirely performance-based, so a repair "
        "that only praises what they do reinforces the fear. Praise who they are, then "
        "stay. The staying is the actual message."
    ),
    repair_scripts=(
        "I'm not going anywhere over this. I'd rather have you annoyed with me than "
        "managing me.",
        "You do a lot for me and I've been sloppy about saying so. That's mine to fix, "
        "and it isn't a reason for you to do more.",
    ),
    boundary_scripts=(
        "I love that you want to help. On this one I need to do it badly by myself first.",
        "I'm going to say no to this, and it doesn't change anything between us.",
        "When you do things for me I didn't ask for, I feel like I owe you. Ask me first "
        "and I'll say yes far more often.",
    ),
    apology_to_them=(
        "Lead with the relationship, not the incident. They need to know the bond held "
        "before they can hear what happened."
    ),
    their_apology=(
        "{subject} apologises by escalating the care — suddenly cooking, fixing, "
        "over-texting. Accept it once, warmly, then say the words for both of you so it "
        "does not turn into another entry on the ledger."
    ),
    safe=(
        "Being asked for something specific and real",
        "Named, concrete appreciation — not general thanks",
        "Being included before the decision, not after",
        "Being told the relationship is not conditional",
    ),
    never=(
        "Call them smothering or say they have no life of their own",
        "Accept the help and then complain about the help",
        "Compare their care to someone else's",
        "Let a big favour pass entirely unremarked",
    ),
    starters=(
        "When was the last time someone took care of you and you actually let them?",
        "What do you want that you've never asked anyone for?",
        "Who checks on you?",
    ),
    hard_conversation=(
        "Start with the bond. One sentence, sincere, before anything else.",
        "Name what they have given, accurately, so the ledger is visibly acknowledged.",
        "Make your ask about your need, never about their excess — excess is the word "
        "that ends the conversation.",
        "Say explicitly what does not change. That sentence is the whole reason they can "
        "hear the rest.",
    ),
    daily_rhythm=(
        "Give one acknowledgement a day, specific enough that it could not apply to "
        "anyone else. It keeps the ledger short, and it costs you almost nothing next "
        "to what an unacknowledged month will cost you."
    ),
    mistaken_for=(
        "This gets mistaken for selflessness. The tell is what happens when the giving is declined: genuine selflessness shrugs, and {subject} will find another way to give it to you anyway, because the giving is doing a job."
    ),
    cheat=CheatSheet(
        say="I noticed you did that. Thank you — specifically for that.",
        never_say="You're being smothering.",
        when_quiet="The ledger is out of balance and they have decided not to mention it. "
                   "Ask what they need, and wait through the first deflection.",
        when_angry="Do not defend. Acknowledge the giving out loud first, then talk.",
        green_flag="They state a preference without being asked twice.",
        red_flag="Sudden bluntness about what they are owed — the stress pattern is live.",
        one_sentence="You don't have to earn this — you already have it.",
    ),
    as_secondary=(
        "a constant read on what everyone in the room needs, which quietly bends their own "
        "plans without them noticing it happening"
    ),
    pull="to be needed and irreplaceable",
    claims=frozenset({"needs-contact", "self-erasing", "image-managed", "over-discloses"}),
)


ARCHETYPES[3] = Archetype(
    type_id=3, name="The Frontrunner", glyph="III",
    title="The one who becomes whatever wins",
    one_line=(
        "{subject} reads the room for what counts as impressive and then becomes it, so "
        "fluently that even they lose track of where the performance stops."
    ),
    core_fear="being worthless without the win — loved for output, and having none",
    core_desire="to be admired, and to have earned it",
    core_lie="I am what I produce. Stop producing and there is nothing underneath.",
    world_view=(
        "Everything is measured, including this. The only safe position is ahead, so they "
        "stay ahead, in whatever the local currency turns out to be."
    ),
    gift=(
        "Momentum. {subject} converts intention into motion faster than anyone you know, "
        "and they bring you with them. Problems that would sit in your life for a year get "
        "solved in a weekend because they simply refuse to lose to one."
    ),
    friction=(
        "You will sometimes be an audience rather than a person. And when they are losing "
        "at something, you get the highlight reel instead of the truth — which is lonely "
        "in a way that is hard to name, because nothing is technically wrong."
    ),
    stress_to=9, stress_text=(
        "The failure mode is not a crash, it is a fade. {subject} goes vague, agreeable, "
        "and strangely unreachable — still functioning, still charming, entirely absent. "
        "A {core_bare} who has stopped competing is not relaxed. They are hiding."
    ),
    growth_to=6, growth_text=(
        "The good direction looks like loyalty over optics: staying with something that is "
        "not going well, admitting a problem before it is solved, choosing the "
        "unimpressive true answer. When {subject} tells you about a failure in progress, "
        "that is not weakness. That is them trusting you."
    ),
    tells=(
        "Reframes a setback as a strategy within seconds",
        "Adjusts their register depending on who is listening",
        "Is uncomfortable being praised for something that came easily",
        "Answers how are you with what they have been doing",
    ),
    triggers=(
        _t("Being seen mid-failure",
           "a fast pivot to logistics, humour, or someone else's problem",
           "they have no script for being watched while losing — the whole system assumes "
           "you show people the finished version",
           "signal in advance that you are not scoring: I don't need the good version. "
           "Tell me the real one"),
        _t("Effort dismissed as luck or talent",
           "a flash of real irritation, quickly smoothed over",
           "if it was luck, it was not earned, and unearned is the same as worthless to "
           "them",
           "credit the work, not the result: I know how much you put into that"),
        _t("Being compared unfavourably, even in passing",
           "an unnecessary counter-fact, delivered pleasantly",
           "comparison is not an opinion to them, it is a ranking, and rankings are real",
           "avoid the comparison entirely — praise them against their own last version"),
        _t("Wasted time",
           "visible restlessness, phone out, a suggestion to wrap it up",
           "idle time is unbanked time, and unbanked time reads as falling behind",
           "give the time a purpose out loud, even a small one, and they will settle "
           "instantly"),
        _t("Being asked what they actually want",
           "a polished answer that is really a description of what is impressive",
           "the honest answer requires knowing themselves apart from the scoreboard, "
           "which is precisely the unbuilt muscle",
           "ask twice, gently, and let the second silence run past comfortable"),
    ),
    deescalation=(
        "You don't have to perform this one for me.",
        "I'm not keeping score. I'm just here.",
        "Tell me the version you'd tell someone who couldn't help you.",
    ),
    repair=(
        "Never force a trade between the apology and their image — the image wins every "
        "time and you get a very smooth non-apology. Give {subject} "
        "a way to concede that costs them no status: go first, concede something real, and "
        "leave the door open without staring at it."
    ),
    repair_scripts=(
        "I'm not looking for you to admit anything. I just want to know what it was "
        "actually like for you.",
        "I went in hard and I was mostly defending myself, not making a point. That's on me.",
    ),
    boundary_scripts=(
        "I'm not competing with you on this, so I'm going to stop responding as though I am.",
        "I need the unpolished version from you. The polished one leaves me on the outside.",
        "You can be busy. I just need to know when you'll actually be here.",
    ),
    apology_to_them=(
        "Keep it short and status-neutral. Long apologies invite an audience dynamic, and "
        "an audience is exactly the thing they cannot be honest in front of."
    ),
    their_apology=(
        "{subject} apologises by delivering — the thing gets done, upgraded, and handed to "
        "you. Take the delivery, then ask for one sentence in words. Over time the "
        "sentence gets easier."
    ),
    safe=(
        "Being valued for effort rather than outcome",
        "A space with no visible scoreboard",
        "Being believed about their ambition instead of teased for it",
        "Permission to be bad at something in front of you",
    ),
    never=(
        "Call them fake, shallow, or all image",
        "Bring up a failure in front of an audience",
        "Compare them to a sibling, an ex, or a peer",
        "Tell them their goal does not matter",
    ),
    starters=(
        "What are you good at that you don't care about at all?",
        "What would you do if it couldn't go on any feed, story, or CV?",
        "When did you last let someone see you lose?",
    ),
    hard_conversation=(
        "Set the frame first: this is not a performance review.",
        "Lead with something you got wrong. They will not go first.",
        "Talk in specifics and outcomes — abstractions read as an attack on character.",
        "End with a concrete next action. An unresolved conversation is unbearable to "
        "them and they will resolve it alone, badly.",
    ),
    daily_rhythm=(
        "Separate connection time from achievement time and say which one you are in. "
        "Ten minutes of explicitly unproductive time with {subject} is worth more than an "
        "hour that they are quietly optimising."
    ),
    mistaken_for=(
        "Easy to mistake for confidence. Confidence does not need the room to agree. Watch {subject} when the room is unimpressed — if the register changes, you are looking at adaptation, not certainty."
    ),
    cheat=CheatSheet(
        say="I don't need the good version. Tell me the real one.",
        never_say="You're so fake.",
        when_quiet="They are losing at something and hiding it. Ask about the thing they "
                   "have stopped mentioning.",
        when_angry="Lower the stakes and remove the audience. They cannot climb down in "
                   "front of anyone.",
        green_flag="They tell you about a failure while it is still happening.",
        red_flag="Agreeable, vague, and unreachable — the fade, not calm.",
        one_sentence="I'm not keeping score — I'm just here.",
    ),
    as_secondary=(
        "an instinct to package things well, so even their private struggles arrive "
        "pre-edited into something presentable"
    ),
    pull="to win and be admired for it",
    claims=frozenset({"image-managed", "future-focused", "decisive", "withholds"}),
)


ARCHETYPES[4] = Archetype(
    type_id=4, name="The Deep Feeler", glyph="IV",
    title="The one who feels it all the way down",
    one_line=(
        "{subject} lives closer to the nerve than you do. What you experience as a mood, "
        "they experience as weather — total, immersive, and impossible to step outside of."
    ),
    core_fear="being ordinary, and therefore forgettable",
    core_desire="to be seen exactly as they are, without translation",
    core_lie="Something essential is missing in me that other people were given.",
    world_view=(
        "Most people are skating over the surface of their own lives. They refuse to, "
        "which is honest and expensive."
    ),
    gift=(
        "Depth with no floor. {subject} will follow you into the worst thing that has ever "
        "happened to you and not flinch, not fix, not rush you out of it. On your darkest "
        "day they are the most useful person you know."
    ),
    friction=(
        "The intensity is not optional and it does not scale down for small occasions. "
        "Ordinary logistics can acquire an emotional weight you did not sign up for, and "
        "you will occasionally feel like a supporting character in a story about feeling."
    ),
    stress_to=2, stress_text=(
        "Under strain {subject} turns outward in a clingy, over-involved way — suddenly "
        "indispensable to someone, over-giving, needing to be needed. It looks like "
        "warmth. It is actually a search for proof that they are wanted."
    ),
    growth_to=1, growth_text=(
        "Growth for {subject} is unglamorous and structural: showing up on a day they do "
        "not feel it, finishing the thing while the mood is wrong. When they are doing the "
        "boring work anyway, they are not betraying their nature — they are at their "
        "strongest."
    ),
    tells=(
        "Remembers the emotional detail of a conversation you have forgotten entirely",
        "Is drawn to whatever is most true rather than most pleasant",
        "Withdraws when they feel misread rather than correcting you",
        "Has a strong physical reaction to environments — light, noise, ugliness",
    ),
    triggers=(
        _t("Being told they are overreacting",
           "instant shutdown, then a long, quiet withdrawal",
           "it confirms the founding suspicion that their inner life is defective rather "
           "than simply larger",
           "validate the size before the content: that sounds like it hit hard"),
        _t("Being treated as interchangeable",
           "a sharp, unexpected coldness after something that seemed fine",
           "generic treatment is the ordinary they most fear; being one of many is worse "
           "than being disliked",
           "be specific about them: reference something only they would have said"),
        _t("Cheerfulness deployed against their mood",
           "a flat look-at-least-you-tried response, then distance",
           "premature optimism reads as being asked to leave before they have arrived",
           "stay in it: I'm not going to talk you out of this. I'll sit here"),
        _t("Being fixed",
           "they stop supplying detail and the conversation goes thin",
           "a solution implies the feeling was a malfunction rather than information",
           "ask permission: do you want help with this or do you want company?"),
        _t("Comparison to how someone else handles it",
           "a very controlled, very final subject change",
           "the comparison says the correct amount of feeling is less than yours",
           "drop comparison entirely — with {subject} it has no upside at all"),
    ),
    deescalation=(
        "I'm not going to talk you out of it. I'm just not leaving.",
        "That makes sense to me — not the size of it, the whole of it.",
        "You're not too much for me.",
    ),
    repair=(
        "Speed is the enemy. {subject} needs the repair to take as long as the rupture "
        "felt, and a fast resolution reads as impatience to be done with them. Go slowly, "
        "stay specific about what you saw them feel, and do not offer a bow at the end."
    ),
    repair_scripts=(
        "I got it wrong, and I think I made you feel like the reaction was the problem. "
        "It wasn't.",
        "I don't need this tied up tonight. I just don't want you in there alone.",
    ),
    boundary_scripts=(
        "I want to hear all of it, and I've got about twenty minutes in me right now. "
        "Can we start and finish tomorrow?",
        "I can be with you in this. I can't be the only place it goes.",
        "When it turns into what's wrong with me, I stop being able to help — that's my "
        "limit, not a judgement.",
    ),
    apology_to_them=(
        "Name the feeling you caused, in their language, before you explain anything. An "
        "explanation offered first will be heard as a defence and nothing after it will "
        "land."
    ),
    their_apology=(
        "{subject} apologises with disproportionate remorse — more than the incident "
        "warrants, sometimes for days. Accept it early and firmly, or the apology becomes "
        "its own event that you then have to manage."
    ),
    safe=(
        "Being met at their actual depth without alarm",
        "Being told they are not too much, in those words",
        "Beauty in the environment — it is not a luxury for them",
        "Being asked what they feel and having the answer be enough",
    ),
    never=(
        "Say you're being dramatic",
        "Compare their reaction to a calmer person's",
        "Rush the resolution to get to peace",
        "Treat their intensity as a phase they will grow out of",
    ),
    starters=(
        "What's something you feel strongly about that you've stopped telling people?",
        "What piece of music, or place, gets you every single time?",
        "When do you feel most like yourself?",
    ),
    hard_conversation=(
        "Choose a time with no hard stop. A deadline turns this into an ambush.",
        "Lead with the feeling, not the fact. The fact is the second thing.",
        "Say the difficult sentence once, plainly, then be quiet long enough for it to be "
        "felt.",
        "Do not close with a summary. Close with a commitment to come back to it.",
    ),
    daily_rhythm=(
        "One unhurried, undistracted stretch beats constant low-grade contact. {subject} "
        "does not need more of your time; they need a piece of it where nothing else is "
        "competing."
    ),
    mistaken_for=(
        "Often mistaken for moodiness. Moodiness passes and leaves nothing behind. What {subject} is doing is closer to permanent high-resolution reception — the feeling is not a weather event, it is the operating temperature."
    ),
    cheat=CheatSheet(
        say="That makes sense to me — the whole of it, not just part.",
        never_say="You're overreacting.",
        when_quiet="They feel misread and have decided not to correct you. Go to them, "
                   "and go specific.",
        when_angry="Match their register down, not up. Calm at them reads as contempt.",
        green_flag="They do the ordinary task anyway on a day the mood is wrong.",
        red_flag="Sudden over-involvement in someone else's life — the stress pattern.",
        one_sentence="You're not too much for me.",
    ),
    as_secondary=(
        "a private undertow of feeling that colours everything, whether or not any of it "
        "reaches the surface"
    ),
    pull="to be met at full depth and never flattened",
    claims=frozenset({"raw-honest", "past-anchored", "over-discloses", "deliberating"}),
)


ARCHETYPES[5] = Archetype(
    type_id=5, name="The Vault", glyph="V",
    title="The one who watches from the doorway",
    one_line=(
        "{subject} pulls back to think, and the pulling back is not a verdict on you. "
        "Nearly every fight you have had with them started by reading it as one."
    ),
    core_fear="being drained — depleted by demands they cannot refuse and cannot meet",
    core_desire="to be competent, self-sufficient, and left with enough of themselves intact",
    core_lie="I have a limited supply of me. Spend it and there is no refill.",
    world_view=(
        "The world takes more than it announces. Understanding it from a safe distance is "
        "the only sustainable way to be in it."
    ),
    gift=(
        "Perspective that is genuinely their own. {subject} has no interest in the "
        "consensus and will tell you what they actually think, having thought about it "
        "properly. When they finally speak on something, it is worth reorganising your "
        "opinion around."
    ),
    friction=(
        "You will be starved of information you need — not withheld from maliciously, just "
        "never volunteered. And they will vanish inward at exactly the moments other "
        "people move closer, which is easy to experience as abandonment."
    ),
    stress_to=7, stress_text=(
        "When overloaded, {subject} scatters. Sudden new interests, uncharacteristic "
        "impulsiveness, a manic-feeling burst of plans. A normally contained person "
        "spraying energy in six directions is not finally having fun; they are running."
    ),
    growth_to=8, growth_text=(
        "Growth looks like taking up space — saying the thing in the room instead of "
        "afterwards, making a decision without a further week of study, being physically "
        "and verbally present. When {subject} states a position immediately, they are at "
        "their best, not their most out of character."
    ),
    tells=(
        "Answers a day later, thoroughly, after everyone else has moved on",
        "Knows an implausible amount about something narrow",
        "Goes quiet in groups and precise one-on-one",
        "Guards their schedule far more than their money",
    ),
    triggers=(
        _t("Emotional demand with no warning",
           "a visible flinch, then flat, minimal, almost robotic answers",
           "an unbudgeted demand hits a resource they experience as finite, and the shutter "
           "comes down automatically",
           "book it: I want to talk about something tonight, it'll take twenty minutes"),
        _t("Being pushed for a feeling in real time",
           "intellectualising — they answer the question with an analysis",
           "the feeling is genuinely not available at that speed; the analysis is not "
           "evasion, it is what has loaded so far",
           "ask in writing, or ask and leave: no answer needed now"),
        _t("Their time being taken without asking",
           "cold irritation out of proportion to the intrusion",
           "unbooked time is the only reliable refill they have, so taking it is taking "
           "the refill",
           "always ask for the slot rather than the answer"),
        _t("Being pulled into a group with no exit",
           "they attach to one person, or to a task, and stop participating",
           "unstructured group time costs them enormously with no visible payoff",
           "agree the exit in advance: we'll leave at nine"),
        _t("Being told they are cold",
           "a shrug, and a real reduction in what they share afterwards",
           "cold names the thing they most fear is true and cannot argue with",
           "name the effort instead: I know reaching out isn't nothing for you"),
    ),
    deescalation=(
        "Take the time you need. I'm not going anywhere and I'm not counting the hours.",
        "You don't have to have a feeling about this right now.",
        "I'd rather have your real answer late than a fast one you don't mean.",
    ),
    repair=(
        "Give {subject} the raw material and then physically leave. They cannot process "
        "and perform at the same time, and being watched while they work something out is "
        "the whole problem. The repair happens in your absence and gets delivered later, "
        "usually more honestly than you expected."
    ),
    repair_scripts=(
        "Here's what I think went wrong, in full. No reply needed tonight.",
        "I crowded you and then read the pullback as rejection. That's a pattern of mine, "
        "not a fact about you.",
    ),
    boundary_scripts=(
        "I can give you space. I need to know roughly when you're coming back.",
        "Silence is fine. Silence with no timeline is the part I can't do.",
        "I'm not asking you to process it out loud. I am asking you to tell me it exists.",
    ),
    apology_to_them=(
        "Short, written, and with no response required. The obligation to reply is the "
        "part that makes an apology feel like another withdrawal from the account."
    ),
    their_apology=(
        "{subject} apologises with information — an unusually complete explanation of "
        "their reasoning. That disclosure is expensive for them and it is the apology. "
        "Receive it as one."
    ),
    safe=(
        "Advance notice of anything emotionally heavy",
        "Time that is genuinely theirs, uncontested",
        "Being asked about what they know",
        "Being allowed to leave the room without a negotiation",
    ),
    never=(
        "Corner them for an immediate answer",
        "Call them cold, robotic, or emotionally unavailable",
        "Volunteer them for something social without asking",
        "Fill their silence with your interpretation of it",
    ),
    starters=(
        "What have you been reading about that nobody's asked you about?",
        "What's a thing everyone believes that you think is just wrong?",
        "What does a genuinely good day with nothing scheduled look like?",
    ),
    hard_conversation=(
        "Give notice. Same day is fine; ambush is not.",
        "Send the substance in writing first so they arrive already processed.",
        "Keep it to one topic. Scope creep is what makes them shut down mid-conversation.",
        "Agree an end time at the start, and honour it exactly — that is what makes the "
        "next one possible.",
    ),
    daily_rhythm=(
        "Low-frequency, high-quality contact. A protected hour where nothing is asked of "
        "{subject} does more for this relationship than daily check-ins, which they "
        "experience as a standing tax."
    ),
    mistaken_for=(
        "Frequently misread as disinterest. Disinterest does not prepare. Ask {subject} about something a week later and watch how much they have quietly thought about it — that is the thing disinterest never does."
    ),
    cheat=CheatSheet(
        say="No reply needed tonight — I just wanted you to have it.",
        never_say="Why are you being so cold?",
        when_quiet="This is baseline, not a signal. Send something with no obligation "
                   "attached and wait.",
        when_angry="Reduce the demand, not the distance. Withdrawing in return reads to "
                   "them as relief, not punishment.",
        green_flag="They volunteer information you didn't ask for.",
        red_flag="Scattered, impulsive, unusually social — the stress pattern, not a "
                 "breakthrough.",
        one_sentence="Take the time you need — I'm not counting the hours.",
    ),
    as_secondary=(
        "a need to retreat and reload that overrides everything else once it hits, "
        "regardless of what the moment seems to require"
    ),
    pull="to keep enough of themselves in reserve",
    claims=frozenset({"needs-space", "withholds", "deliberating", "avoids-conflict"}),
)


ARCHETYPES[6] = Archetype(
    type_id=6, name="The Sentinel", glyph="VI",
    title="The one who is already scanning for the exit",
    one_line=(
        "{subject} has run the disaster in their head before you finished the sentence. "
        "It is exhausting to live inside and it is why nothing catastrophic ever catches "
        "this family off guard."
    ),
    core_fear="being without support when it finally goes wrong",
    core_desire="security — and people who will still be standing there when it does",
    core_lie="If I stop scanning, that is exactly when it happens.",
    world_view=(
        "The floor is not as solid as everyone is pretending. Someone has to be checking, "
        "and everyone else has clearly declined."
    ),
    gift=(
        "Loyalty that does not require conditions and does not expire. {subject} stays. "
        "Through the bad news, the money trouble, the version of you that was hard to like — they "
        "stay, and they have already thought about what could go wrong next and packed for "
        "it."
    ),
    friction=(
        "The scanning does not stay in their head. It arrives as questions that feel like "
        "doubt, worst cases attached to your good news, and a testing behaviour where they "
        "poke at your commitment to check it is real — which, done often enough, wears "
        "exactly the thing they are testing."
    ),
    stress_to=3, stress_text=(
        "Under pressure {subject} goes into overdrive — busy, competent, image-focused, "
        "solving furiously. It looks like they are coping well. They are outrunning the "
        "anxiety, and it will surface later, larger, usually at you."
    ),
    growth_to=9, growth_text=(
        "The relief valve is settledness: {subject} letting a thing be fine without "
        "checking it. When they say I don't know and it doesn't bother me, believe it and "
        "do not disturb it. Those hours are rarer for them than for anyone else you know."
    ),
    tells=(
        "Asks a clarifying question that is really a risk assessment",
        "Remembers who was unreliable, and when, in detail",
        "Warms up dramatically once you are inside the circle",
        "Second-guesses a decision out loud after it has been made",
    ),
    triggers=(
        _t("Vagueness about plans",
           "escalating questions that feel like an interrogation",
           "unspecified is indistinguishable from unsafe; the questions are them trying to "
           "get the floor back",
           "over-specify by default — time, place, duration, and when you will next check in"),
        _t("A commitment quietly changed",
           "disproportionate reaction to a small schedule change",
           "the change is not the issue; it is data suggesting commitments here are "
           "provisional",
           "flag it early and explain the why. The why is what stops the spiral"),
        _t("Reassurance with nothing behind it",
           "they argue with the reassurance and seem to want to be worried",
           "empty comfort proves nobody is really looking, which increases the threat",
           "engage the specific worst case seriously — that is what actually calms them"),
        _t("Being told they are paranoid",
           "a hurt, defensive litany of every time they were right",
           "the scanning is their contribution; calling it a defect deletes the "
           "contribution and the person",
           "credit the catch: you were right about the last one, so tell me this one"),
        _t("Authority acting arbitrarily",
           "immediate, immovable resistance, disproportionate to the stake",
           "arbitrary power is the original wound; the resistance is not about this "
           "instance",
           "give them the reasoning and a say. Both, not one"),
    ),
    deescalation=(
        "Let's plan for the version where it goes wrong. What would we actually do?",
        "You've been right about this before. I'm listening.",
        "I'm not going anywhere, and you don't have to test that to find out.",
    ),
    repair=(
        "Reassurance alone makes it worse — it sounds like being managed. {subject} needs "
        "the worst case addressed out loud and a concrete, checkable commitment. Then keep "
        "the commitment exactly, once, visibly. One kept promise is worth a hundred "
        "sentences to this one."
    ),
    repair_scripts=(
        "You're worried I'll do it again. That's fair. Here's specifically what I'm going "
        "to do differently, and you can hold me to it.",
        "I don't think you're overreacting. I think I gave you a real reason to check.",
    ),
    boundary_scripts=(
        "I'll answer the question once, properly. I can't answer it four times — that's "
        "when I start to shut down.",
        "Ask me directly instead of testing it. I'll always tell you the truth if you ask.",
        "I can plan the disaster with you. I can't live inside it all evening.",
    ),
    apology_to_them=(
        "Attach a mechanism. An apology with no how-this-won't-happen-again is just noise "
        "to them, however sincere it sounds."
    ),
    their_apology=(
        "{subject} apologises by getting anxious about whether you are still okay with "
        "them — repeat check-ins, are we good, a slight over-correction. Answer clearly "
        "the first time and the loop closes; answer vaguely and it runs all week."
    ),
    safe=(
        "Specifics — times, plans, what happens next",
        "Being told the commitment holds, unprompted",
        "Having their worry taken seriously rather than soothed",
        "Consistency, which outperforms grand gestures every time",
    ),
    never=(
        "Say you're being paranoid or you always do this",
        "Change a plan and hope they do not notice",
        "Give an ambiguous answer to a direct question",
        "Joke about leaving, even obviously",
    ),
    starters=(
        "What's the thing you keep preparing for that you've never told anyone about?",
        "Who's the person you'd call at 3am, and do they know that?",
        "What did you worry about at fifteen that turned out to be nothing?",
    ),
    hard_conversation=(
        "Say up front where this ends. An open-ended difficult conversation is a threat.",
        "Name the worst thing they are afraid you are about to say, and say whether it is "
        "that.",
        "Deal in specifics and mechanisms, not intentions.",
        "Close with the next checkpoint. A defined next contact is what lets them sleep.",
    ),
    daily_rhythm=(
        "Predictability beats intensity. The same small contact at the same time does more "
        "for {subject} than an unpredictable grand gesture, which mostly registers as a "
        "variable."
    ),
    mistaken_for=(
        "Commonly mistaken for negativity. A negative person expects the worst and does nothing. {subject} expects the worst and packs for it, then stays through it. The scanning is not pessimism; it is a form of commitment."
    ),
    cheat=CheatSheet(
        say="Let's plan for the version where it goes wrong.",
        never_say="You're being paranoid.",
        when_quiet="They are running a scenario and have decided not to burden you. Ask "
                   "what the worst case is, seriously.",
        when_angry="Do not reassure. Address the specific risk and commit to something "
                   "checkable.",
        green_flag="They let something be fine without verifying it.",
        red_flag="Frantic productivity and image management — the stress pattern.",
        one_sentence="You don't have to test it — I'm not going anywhere.",
    ),
    as_secondary=(
        "a background threat-scan that keeps running underneath everything else, so even "
        "their confident moments have a contingency attached"
    ),
    pull="to know the ground will hold",
    claims=frozenset({"needs-contact", "deliberating", "past-anchored", "raw-honest"}),
)


ARCHETYPES[7] = Archetype(
    type_id=7, name="The Escape Artist", glyph="VII",
    title="The one who leaves before it can hurt",
    one_line=(
        "{subject} is the best day of your month and the hardest person to find on the "
        "worst one. Both facts come from the same place."
    ),
    core_fear="being trapped in pain with no way out",
    core_desire="freedom, and enough good ahead to outrun what is behind",
    core_lie="If I keep moving, it cannot land on me.",
    world_view=(
        "There is always something better available and no good reason to sit in this. "
        "Life is short and mostly upside, if you refuse to look at it for too long."
    ),
    gift=(
        "They make life bigger. {subject} turns an ordinary Tuesday into something you "
        "still talk about, turns a disaster into a story you can survive, and drags you "
        "out of ruts you had stopped noticing. Their optimism is not naive — it is load-"
        "bearing, for both of you."
    ),
    friction=(
        "They are structurally unavailable for the heavy part. The moment a conversation "
        "gets genuinely painful, a joke arrives, or a plan, or a change of subject — and "
        "you end up carrying the hard things by yourself while technically being in a "
        "relationship with someone delightful."
    ),
    stress_to=1, stress_text=(
        "Cornered, {subject} turns rigid and critical — suddenly rule-bound, sharp about "
        "other people's failings, joyless. A normally expansive person going hard and "
        "narrow is not maturing. They are trapped and it is coming out sideways."
    ),
    growth_to=5, growth_text=(
        "The good direction is depth over motion: staying with one thing, going quiet, "
        "finishing something unglamorous. When {subject} sits still through something "
        "difficult without reaching for the exit, that is the whole growth arc in one "
        "moment. Notice it out loud."
    ),
    tells=(
        "Has three plans for a weekend that has not been agreed",
        "Reframes their own bad news as a funny story within a day",
        "Changes the subject the instant it gets heavy",
        "Is genuinely excellent in a crisis and unavailable in a grief",
    ),
    triggers=(
        _t("An open-ended heavy conversation",
           "humour, a tangent, or a sudden need to be somewhere",
           "no visible end means no exit, and no exit is the actual phobia",
           "put a wall on it: fifteen minutes, then we're done and we go do something"),
        _t("Being pinned to a commitment",
           "vagueness, over-agreement, then a late change",
           "commitment feels like a closing door rather than a plan",
           "frame it as a choice they keep: pick which night, and it's yours to move once"),
        _t("Being called flaky or shallow",
           "a fast joke, then a real and lasting distance",
           "it names the fear that the lightness is all there is and nothing underneath "
           "is real",
           "credit the depth you have seen: you were the only one who stayed that night"),
        _t("Repetition and routine with no horizon",
           "restlessness, then an out-of-nowhere disruptive suggestion",
           "sameness with nothing ahead reads as being buried alive",
           "keep something on the calendar. A future good thing makes the present "
           "endurable"),
        _t("Someone else's sustained pain",
           "over-solving, forced brightness, or disappearing",
           "they have no tolerance for pain they cannot fix, and no script for staying "
           "in it",
           "give them a role: I don't need you to fix it. Sit here and distract me at nine"),
    ),
    deescalation=(
        "Fifteen minutes on the hard thing, then we go do something good. I'll watch the "
        "clock.",
        "I'm not trying to trap you. I'm trying to be known by you.",
        "You don't have to fix this. Staying is the whole job.",
    ),
    repair=(
        "Bound it. {subject} will engage properly with almost anything if the exit is "
        "visible and honoured — and will engage with nothing if it is not. Set a clear "
        "duration, do the real work inside it, then genuinely stop and do something good "
        "together. Break the boundary once and you lose the mechanism for a year."
    ),
    repair_scripts=(
        "Ten minutes, real talk, then we drop it and go out. I mean the drop it part.",
        "I cornered you and then got annoyed that you left. That's a bad combination and "
        "it was mine.",
    ),
    boundary_scripts=(
        "I need this one to actually finish, not turn into a joke. Then it's done for good.",
        "You can say no to the plan. I need you to say no, rather than yes and then "
        "disappear.",
        "I love the fun version. I need about an hour a week of the other one.",
    ),
    apology_to_them=(
        "Short, warm, and with a clear ending. A long apology becomes an enclosure and "
        "they will start looking for the door while you are still talking."
    ),
    their_apology=(
        "{subject} apologises with an experience — a plan, a gift, an extremely good day "
        "engineered on your behalf. It is sincere. Accept it, then ask for one sentence "
        "out loud so the thing itself gets named."
    ),
    safe=(
        "A visible exit from anything heavy",
        "Something good on the calendar ahead",
        "Being recognised for the times they did stay",
        "Options preserved wherever it does not cost you anything",
    ),
    never=(
        "Trap them in an unbounded conversation to make a point",
        "Call them flaky, shallow, or a child",
        "Punish them for the one time they showed up late to the heavy thing",
        "Cancel everything they were looking forward to, as leverage",
    ),
    starters=(
        "What's the best day you've had this year, and what made it that?",
        "What's the one thing you've stuck with that surprised you?",
        "What are you avoiding right now?",
    ),
    hard_conversation=(
        "State the duration first and mean it.",
        "One topic only. A second topic proves the exit was fake.",
        "Ask for a specific behaviour, not an emotional acknowledgement.",
        "End it on time and then genuinely change the mood. That is what buys you the "
        "next conversation.",
    ),
    daily_rhythm=(
        "Anchor the week with one good thing ahead and one bounded serious conversation. "
        "{subject} can carry a surprising amount of weight when they can see where they "
        "get to put it down."
    ),
    mistaken_for=(
        "Misread as shallow more than any other pattern. Shallow does not notice the hard thing. {subject} notices it precisely, and then moves — the speed is a measure of how much it landed, not how little."
    ),
    cheat=CheatSheet(
        say="Fifteen minutes on this, then we go do something good.",
        never_say="You never take anything seriously.",
        when_quiet="Something landed that they cannot outrun. Go to them and keep it "
                   "short and light-footed.",
        when_angry="Give them the exit before the point. They cannot hear anything while "
                   "they feel enclosed.",
        green_flag="They stay in a hard conversation past the point it stops being fun.",
        red_flag="Rigid, critical, joyless — the stress pattern, not maturity.",
        one_sentence="I'm not trying to trap you — I'm trying to be known by you.",
    ),
    as_secondary=(
        "a reflex toward the exit whenever things get heavy, so their engagement has a "
        "half-life they are not choosing"
    ),
    pull="to stay free and keep the exits open",
    claims=frozenset({"future-focused", "needs-space", "avoids-conflict", "decisive"}),
)


ARCHETYPES[8] = Archetype(
    type_id=8, name="The Force", glyph="VIII",
    title="The one who protects by pushing",
    one_line=(
        "{subject} would rather have the fight now than the resentment later, and they "
        "genuinely cannot understand why everyone else prefers it the other way round."
    ),
    core_fear="being controlled, or being the one who is defenceless",
    core_desire="to protect their own and never be at anyone's mercy",
    core_lie="Softness gets punished. Get there first.",
    world_view=(
        "Power is the only honest subject. Everyone is using it; most people lie about it. "
        "They would rather be the one who says so."
    ),
    gift=(
        "Total protection. If you are inside {subject_poss} circle, they will go through "
        "anything for you, absorb costs they will never mention, and stand in front of "
        "things you did not know were coming. Nobody else in your life is that "
        "unconditional about the hard part."
    ),
    friction=(
        "The volume is not calibrated. What they experience as directness lands on you as "
        "force, and by the time you have recovered enough to respond, they have moved on "
        "and consider the matter closed. You lose arguments you were winning simply by "
        "flinching."
    ),
    stress_to=5, stress_text=(
        "Under real threat {subject} does not get louder, they disappear. They go "
        "strategic, contained, and cold — withdrawing to somewhere they cannot be reached "
        "while they work out the play. A silent {core_name} is more concerning than a loud "
        "one, not less."
    ),
    growth_to=2, growth_text=(
        "Growth for {subject} is unguarded care. Protecting someone in a way that exposes "
        "them, admitting a need, letting the softness show without a joke to cover it. "
        "When they show you the tender thing, do not comment on how rare it is. Just "
        "receive it and keep going."
    ),
    tells=(
        "Says the thing everyone was avoiding, immediately",
        "Escalates instantly when someone they love is threatened",
        "Has no interest in a conversation with no stakes",
        "Respects you more after you have pushed back on them",
    ),
    triggers=(
        _t("Being handled or managed",
           "an instant hard edge and a direct question about what you are actually doing",
           "manipulation is the one unforgivable thing; a soft approach reads as a "
           "manoeuvre",
           "be blunt to the point of discomfort. Bluntness is the register they trust"),
        _t("Someone under their protection being harmed",
           "immediate, disproportionate escalation aimed at whoever is responsible",
           "protection is the identity, so a breach is not an event, it is a failure of "
           "self",
           "give them a real job in the response. Uselessness is what turns it into rage"),
        _t("Being lied to about something small",
           "a permanent, quiet recalibration of how much you get told",
           "a small lie is proof the big ones are available; they do not distinguish by "
           "size",
           "tell the unflattering truth first and fast. It costs you far less than you "
           "think"),
        _t("Weakness they are expected to pretend not to see",
           "brutal honesty at the worst possible moment",
           "pretending is a form of lying, and lying is the thing",
           "get there first: I know this looks bad, here's what I'm actually doing"),
        _t("Being told to calm down",
           "an escalation, every single time, without exception",
           "it is an instruction from someone claiming authority they were not given — the "
           "exact wound",
           "hold your ground without matching volume: I'm not backing off, and I'm not "
           "doing it at this volume"),
    ),
    deescalation=(
        "I'm not going to fold, and I'm not going to fight you at this volume.",
        "You don't have to protect me from this one. I want you next to me, not in front "
        "of me.",
        "I'm telling you the unflattering version because you'd rather have it.",
    ),
    repair=(
        "{subject} does not want a careful apology, they want the truth at full strength "
        "and then normal life resumed immediately. Do not tiptoe and do not extend it. Say "
        "the real thing, take your share without flinching, and then be entirely normal "
        "within the hour — the fast return to normal is how they know it is genuinely over."
    ),
    repair_scripts=(
        "I was wrong and I knew it halfway through. I kept going because I didn't want to "
        "lose.",
        "You came in too hard and I'm not going to pretend otherwise. I still know why you "
        "did it.",
    ),
    boundary_scripts=(
        "I'll have this conversation. Not at this volume.",
        "I don't need defending here. I need you to let me handle it and be there if it "
        "goes badly.",
        "You can disagree with me as hard as you want. You can't decide it for me.",
    ),
    apology_to_them=(
        "Direct, no cushioning, no explanatory clause. Anything softened reads as a "
        "manoeuvre and gets treated as one."
    ),
    their_apology=(
        "{subject} apologises through action and proximity — a bill quietly paid, a "
        "problem removed, a sudden and total availability. The words may never come. The "
        "presence is not a substitute for them; it is the form the apology takes."
    ),
    safe=(
        "Directness, even when it is unwelcome",
        "Being pushed back on without fear",
        "Having something real to protect",
        "Being trusted with the ugly truth first",
    ),
    never=(
        "Say calm down or you're too much",
        "Go behind them to get a decision changed",
        "Soften bad news into something they later discover was softened",
        "Make their protectiveness the punchline in company",
    ),
    starters=(
        "Who protected you when you were small?",
        "What's the thing you'd never let happen to someone you love?",
        "When did you last let someone else take the lead and it was fine?",
    ),
    hard_conversation=(
        "Open at full strength. A run-up gets read as a manoeuvre.",
        "Do not soften the ask. Say the actual thing, in one sentence.",
        "Hold your position under pressure — folding costs you their respect permanently.",
        "Return to normal fast afterwards. Extending it makes it a grudge, and grudges are "
        "what they are afraid of.",
    ),
    daily_rhythm=(
        "Say the true thing early and at full size. {subject} handles hard information "
        "well and handles being protected from it very badly — nearly every serious "
        "rupture with them starts as a kindness."
    ),
    mistaken_for=(
        "Regularly mistaken for anger. Anger wants to hurt something. {subject} wants the thing settled and back to normal, and will be entirely fine with you an hour later, which is the part that genuinely confuses people."
    ),
    cheat=CheatSheet(
        say="Here's the unflattering version, because you'd rather have it.",
        never_say="Calm down.",
        when_quiet="This is the serious one. Silence means strategy, not peace — go to "
                   "them directly and ask.",
        when_angry="Do not match volume and do not retreat. Both are read as answers.",
        green_flag="They let the soft thing show without covering it with a joke.",
        red_flag="Cold, contained, strategically absent — the stress pattern.",
        one_sentence="I want you next to me, not in front of me.",
    ),
    as_secondary=(
        "an instinct to take control the moment something feels unsafe, which arrives "
        "faster than any of their other reactions"
    ),
    pull="to stay in control and protect their own",
    claims=frozenset({"seeks-conflict", "decisive", "raw-honest", "self-asserting"}),
)


ARCHETYPES[9] = Archetype(
    type_id=9, name="The Peacekeeper", glyph="IX",
    title="The one who disappears to keep the peace",
    one_line=(
        "{subject} is the easiest person in your life to be around and the hardest to "
        "actually reach, and those are not two separate facts."
    ),
    core_fear="conflict that severs the connection — being cut off, or causing it",
    core_desire="peace, and everyone still in the room at the end",
    core_lie="If I take up space, something breaks.",
    world_view=(
        "Most conflict is not worth what it costs. The comfortable position is to have no "
        "position, so that is where they live."
    ),
    gift=(
        "They lower the temperature of everything. {subject} can hold two people who "
        "cannot stand each other in the same room and make it survivable. Around them your "
        "nervous system settles, and you almost certainly under-value this because they "
        "have never once made it visible."
    ),
    friction=(
        "You do not know what they think, and eventually you stop being able to find them. "
        "The agreement is not agreement, it is absence — and then one day something small "
        "detonates and turns out to have been accumulating for eleven months."
    ),
    stress_to=6, stress_text=(
        "Pushed too far, {subject} becomes anxious and suspicious — asking pointed "
        "questions, reading motives into things, unable to settle. A normally easy person "
        "going watchful means the peace has stopped working and they no longer trust the "
        "floor."
    ),
    growth_to=3, growth_text=(
        "Growth is showing up with a stake in it: stating a preference, starting the thing "
        "they have described for years, taking a side. When {subject} says I want, without "
        "hedging, treat it as significant. It cost more than it looked like."
    ),
    tells=(
        "Agrees, then quietly does not do it",
        "Deflects a preference question back at you",
        "Is unbothered by things that would enrage anyone else",
        "Goes on autopilot — TV, phone, small tasks — rather than into a conflict",
    ),
    triggers=(
        _t("Being pressured for an immediate position",
           "a rapid, hollow agreement that will not survive the week",
           "under pressure the fastest route to peace is agreement, so that is what comes "
           "out regardless of what is true",
           "remove the deadline: think about it, tell me tomorrow, and I'd rather have "
           "your real answer"),
        _t("Raised voices anywhere near them",
           "physical stillness, then a total mental exit",
           "conflict volume triggers a shutdown that is closer to a reflex than a decision",
           "drop your volume before your content. They cannot process the content until "
           "the volume moves"),
        _t("Being told they do not care",
           "a rare flash of real hurt, then a deeper withdrawal",
           "they care enormously and have optimised entirely for not showing it; the "
           "accusation deletes them",
           "credit what you have seen: you were the one who kept us all speaking"),
        _t("A long-buried complaint being dismissed once more",
           "an out-of-proportion eruption over something trivial",
           "that is not the incident, it is the archive, and it has been full for a while",
           "ask periodically and wait through the deflection: what's the thing you've not "
           "said?"),
        _t("Being managed toward a decision",
           "passive resistance — agreement, delay, and quiet non-compliance",
           "they will not fight you for the wheel; they will simply not drive",
           "offer real options instead of a preferred outcome dressed as a choice"),
    ),
    deescalation=(
        "I'd rather disagree with you than not know where you are.",
        "You can take a side here. It's not going to break anything.",
        "Take the time. I want your actual answer, not the fast one.",
    ),
    repair=(
        "The urge is to smooth it over and move on, and if you let that happen the thing "
        "gets filed rather than resolved. Slow it down and ask directly for the "
        "dissatisfaction — expect to ask three times. The first two answers will be it's "
        "fine. The third one is the real one, and it is worth the wait."
    ),
    repair_scripts=(
        "I don't want the easy version. What's the part you didn't say?",
        "I steamrolled you and you let me, and I noticed. Let's go back to where you "
        "stopped talking.",
    ),
    boundary_scripts=(
        "It's fine isn't enough for me here. I need the real one, and I'll wait.",
        "If you agree now and don't do it later, that's the thing that actually hurts.",
        "You're allowed to say no to me. I'd much rather have that.",
    ),
    apology_to_them=(
        "Be gentle, be brief, and be explicit that the relationship is not in danger — "
        "that fear is what makes them agree to anything just to end it."
    ),
    their_apology=(
        "{subject} apologises by restoring normality — a cup of tea, a light comment, "
        "everything back to how it was. That is genuine, and it is also the file being "
        "closed early. Take the tea, then ask the real question anyway."
    ),
    safe=(
        "No time pressure on anything that requires an opinion",
        "Being asked what they want, repeatedly and patiently",
        "Low volume, low stakes, no ultimatums",
        "Being told disagreement is survivable here",
    ),
    never=(
        "Force an immediate position with an audience present",
        "Say you don't even care or you have no opinions",
        "Interpret their agreement as consent and act on it",
        "Escalate volume to get a reaction — you will get compliance and lose the person",
    ),
    starters=(
        "What would you do with a week that was entirely yours?",
        "What's something you disagree with me about and never bothered to say?",
        "What's the thing you'd do if you knew nobody would be annoyed?",
    ),
    hard_conversation=(
        "Reduce the stakes explicitly before you start: this isn't a big deal, I just want "
        "the truth.",
        "Ask an open question and let a long silence run without rescuing it.",
        "When you get a hedge, say thank you and ask once more. The second ask is the "
        "one that gets you something true.",
        "Confirm what you heard back to them, and check it. They will correct a "
        "misquote when they would never have volunteered the original.",
    ),
    daily_rhythm=(
        "Ask for one small preference every day — the restaurant, the film, the plan — and "
        "then actually go with it. That is how {subject} relearns that having a position "
        "does not cost anything here."
    ),
    mistaken_for=(
        "Almost always mistaken for agreement. Agreement holds up under a follow-up question. What {subject} offers is closer to a truce, and truces expire quietly rather than being renegotiated."
    ),
    cheat=CheatSheet(
        say="I'd rather disagree with you than not know where you are.",
        never_say="You don't even care.",
        when_quiet="Quiet is their default, but agreement plus quiet means something is "
                   "being filed. Ask a third time.",
        when_angry="This is the archive, not the incident. Ask what else is in there.",
        green_flag="They state a preference and hold it under mild pressure.",
        red_flag="Watchful, anxious, suspicious of motives — the stress pattern.",
        one_sentence="You can take a side here — it isn't going to break anything.",
    ),
    as_secondary=(
        "a strong pull toward whatever keeps the peace, which quietly overrides their own "
        "position before they have finished forming it"
    ),
    pull="to keep the peace and stay connected",
    claims=frozenset({"avoids-conflict", "self-erasing", "needs-contact", "deliberating"}),
)


# --------------------------------------------------------------------------
# Relationship lenses
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RelationshipLens:
    """What changes about the advice because of *who* this person is to you.

    The archetype supplies the pattern; the lens supplies the stakes, the
    channel, the power dynamic and the realistic repair window. Together
    they cover all 45 combinations without 45 separate manuals.
    """

    slug: str
    stakes: str
    power: str
    channel: str
    ask_form: str
    repair_window: str
    history: str          # how the past shapes the present here
    limits: str           # what you cannot change in this relationship
    leverage: str         # the one move with outsized return here


LENSES: dict[str, RelationshipLens] = {
    "mom": RelationshipLens(
        slug="mom",
        stakes=(
            "This is the relationship your nervous system was built inside, which is why a "
            "four-word text from her can rearrange your whole afternoon at thirty-five."
        ),
        power=(
            "The old hierarchy is still running in the background even though you are both "
            "adults. Neither of you fully believes it and neither of you has replaced it, "
            "so most conflicts are actually about which version of the relationship you "
            "are in."
        ),
        channel="a phone call she initiates, or a text thread with an unpredictable half-life",
        ask_form="a direct ask, made once, without the childhood tone creeping in",
        repair_window="days rather than hours — this relationship absorbs delay better than most",
        history=(
            "Everything here has a twenty-year prologue. The current disagreement is "
            "rarely the actual subject, and treating it as though it is will keep you "
            "arguing about the dishwasher for the rest of your life."
        ),
        limits=(
            "You are not going to reparent her and you are not going to win the "
            "retrospective argument about your childhood. What is available is a different "
            "present, which is more than it sounds like."
        ),
        leverage=(
            "Adult-to-adult framing, used consistently. Every time you respond as a peer "
            "rather than as her kid, you move the relationship a little further into the "
            "present tense."
        ),
    ),
    "dad": RelationshipLens(
        slug="dad",
        stakes=(
            "Whatever was never said here is still the loudest thing in the room, and the "
            "silence has usually been mistaken by both of you for peace."
        ),
        power=(
            "The authority structure has probably softened without ever being formally "
            "renegotiated. He may not know the terms have changed; you may still be "
            "asking permission for things that no longer require it."
        ),
        channel="side-by-side activity, practical logistics, and text messages that are shorter than they look",
        ask_form="a concrete request attached to something practical, rather than an emotional preamble",
        repair_window="long — but the longer it runs, the more it calcifies into the permanent version",
        history=(
            "There is a good chance the emotional vocabulary here was never installed by "
            "anyone, in either direction. That is not the same as absence of feeling, and "
            "confusing the two costs people decades."
        ),
        limits=(
            "He is unlikely to become fluent in a language he was never taught. You can "
            "get honesty, presence and consistency; a full emotional retrospective is "
            "usually not on the menu."
        ),
        leverage=(
            "Do a thing alongside him and talk while doing it. Face-to-face makes this "
            "harder; shoulder-to-shoulder makes it possible."
        ),
    ),
    "boyfriend": RelationshipLens(
        slug="boyfriend",
        stakes=(
            "This is the one you are choosing daily, which makes every unresolved pattern "
            "compound rather than settle. Nothing here stays the same size."
        ),
        power=(
            "Nominally equal, actually negotiated constantly — over time, attention, whose "
            "stress sets the temperature of the week. Most couples never name this, and "
            "then argue about its symptoms."
        ),
        channel="daily contact, shared logistics, and the ten minutes before sleep where most real things get said",
        ask_form="a specific, present-tense request about behaviour, not a verdict about character",
        repair_window="short — under twenty-four hours, before it joins the permanent record",
        history=(
            "Every unresolved argument here gets referenced in the next one. The archive "
            "is live, mutual, and admissible, which is why unfinished conflicts are more "
            "expensive in this relationship than any other."
        ),
        limits=(
            "You cannot make him want to change. You can make it safe and specific enough "
            "that the version of him that already wants to has somewhere to stand."
        ),
        leverage=(
            "Fix the repair time, not the conflict rate. Couples who recover quickly beat "
            "couples who argue rarely, by a wide margin."
        ),
    ),
    "girlfriend": RelationshipLens(
        slug="girlfriend",
        stakes=(
            "This is the one you are choosing daily, which makes every unresolved pattern "
            "compound rather than settle. Nothing here stays the same size."
        ),
        power=(
            "Nominally equal, actually negotiated constantly — over time, attention, whose "
            "stress sets the temperature of the week. Most couples never name this, and "
            "then argue about its symptoms."
        ),
        channel="daily contact, shared logistics, and the ten minutes before sleep where most real things get said",
        ask_form="a specific, present-tense request about behaviour, not a verdict about character",
        repair_window="short — under twenty-four hours, before it joins the permanent record",
        history=(
            "Every unresolved argument here gets referenced in the next one. The archive "
            "is live, mutual, and admissible, which is why unfinished conflicts are more "
            "expensive in this relationship than any other."
        ),
        limits=(
            "You cannot make her want to change. You can make it safe and specific enough "
            "that the version of her that already wants to has somewhere to stand."
        ),
        leverage=(
            "Fix the repair time, not the conflict rate. Couples who recover quickly beat "
            "couples who argue rarely, by a wide margin."
        ),
    ),
    "best-friend": RelationshipLens(
        slug="best-friend",
        stakes=(
            "This relationship has no external scaffolding. No shared address, no legal "
            "tie, no obligation — it survives entirely on the two of you choosing to "
            "maintain it, which makes drift the only real threat."
        ),
        power=(
            "Genuinely equal, which sounds simple and is not: with no structure to fall "
            "back on, neither of you has standing to demand anything, so unspoken "
            "grievances tend to become distance instead of conflict."
        ),
        channel="irregular bursts — a long overdue call, a fast thread, months of nothing that mean nothing",
        ask_form="a plain, unweighted ask that does not turn the friendship into a negotiation",
        repair_window="weeks, but the risk is not explosion, it is quiet permanent drift",
        history=(
            "You have both changed substantially since this friendship formed its habits, "
            "and neither of you has fully updated their model of the other. Most friction "
            "here is running on an outdated file."
        ),
        limits=(
            "You cannot manufacture proximity or obligation. What you can do is be the one "
            "who reliably initiates, which in practice decides whether this friendship "
            "survives your thirties."
        ),
        leverage=(
            "Name the drift out loud once. Friendships almost never end from a fight; they "
            "end from nobody being willing to say I miss this."
        ),
    ),
}


# --------------------------------------------------------------------------
# How each archetype expresses itself specifically in each kind of bond.
# Three kinds x nine types = the relationship-awareness that stops the copy
# reading like a generic horoscope.
# --------------------------------------------------------------------------

KIND_FRAMING: dict[tuple[str, int], str] = {
    ("parent", 1): "As a parent, the standard landed on you before you could evaluate it, so their corrections still arrive with more authority than they have earned.",
    ("parent", 2): "As a parent, the giving came with an unspoken invoice you have been paying since childhood, usually in guilt rather than in anything visible.",
    ("parent", 3): "As a parent, their achievements were the family weather, and your own were quietly graded against them — often without either of you naming it.",
    ("parent", 4): "As a parent, their emotional weather set the temperature of the whole house, and you learned to read it before you learned to read.",
    ("parent", 5): "As a parent, their withdrawal read to a child as absence, and some part of you is still checking whether you were the reason.",
    ("parent", 6): "As a parent, their vigilance felt like the world was dangerous rather than like they were frightened, and you may have inherited the alarm without the context.",
    ("parent", 7): "As a parent, they were the fun one, and the cost of that was that the heavy things had nowhere to go and often ended up with you.",
    ("parent", 8): "As a parent, their force was not calibrated for someone small, and you learned early either to match it or to disappear beneath it.",
    ("parent", 9): "As a parent, their peace-keeping meant conflicts never resolved, only submerged, and you grew up fluent in a quiet that was not actually calm.",

    ("partner", 1): "In a partnership, the standard has nowhere to hide: it shows up in the kitchen, the finances and the way you load a dishwasher, daily.",
    ("partner", 2): "In a partnership, the ledger runs hot, because the sheer volume of daily care makes the imbalance both larger and harder to see.",
    ("partner", 3): "In a partnership, you are the one person who sees behind the performance, which is both the intimacy and the threat.",
    ("partner", 4): "In a partnership, the intensity has nowhere to dissipate, so ordinary domestic friction can acquire an emotional scale that genuinely surprises you.",
    ("partner", 5): "In a partnership, their need for reserve collides with the constant low-level demand of sharing a life, and neither of you is wrong about it.",
    ("partner", 6): "In a partnership, you are the primary security object, which means their anxiety is aimed at you precisely because you matter most.",
    ("partner", 7): "In a partnership, the exit reflex reads as a threat to the relationship itself, even when it is only ever a threat to the conversation.",
    ("partner", 8): "In a partnership, their protection and their control are the same behaviour pointed in different directions, and telling them apart is most of the work.",
    ("partner", 9): "In a partnership, the agreeableness looks like harmony for years, right up until the archive opens and neither of you recognises the argument.",

    ("peer", 1): "Between friends, the corrections have no authority behind them, which makes them easier to ignore and easier to resent quietly for a decade.",
    ("peer", 2): "Between friends, they will be the one who organises everything, and the imbalance builds silently because nobody is tracking it out loud.",
    ("peer", 3): "Between friends, comparison is the live wire — your wins register on a scoreboard they cannot switch off, even when they are happy for you.",
    ("peer", 4): "Between friends, they will go to the depths with you that nobody else will, and will withdraw hard the moment they feel like a supporting character.",
    ("peer", 5): "Between friends, long silences genuinely mean nothing, and treating them as a verdict is the single most common way this friendship gets damaged.",
    ("peer", 6): "Between friends, loyalty is the entire currency, and one unexplained absence gets weighted far more heavily than five years of showing up.",
    ("peer", 7): "Between friends, they are the best company you have and the hardest person to reach during a grief, and both are the same trait.",
    ("peer", 8): "Between friends, they will defend you to anyone and steamroll you personally, sometimes in the same evening.",
    ("peer", 9): "Between friends, the friendship can drift for years without a single conflict, because neither of you will be the one to say the thing.",
}


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

_REQUIRED_TUPLE_SIZES: Mapping[str, tuple[int, int]] = {
    "tells": (4, 6),
    "triggers": (5, 5),
    "deescalation": (3, 3),
    "repair_scripts": (2, 3),
    "boundary_scripts": (3, 3),
    "safe": (4, 5),
    "never": (4, 5),
    "starters": (3, 3),
    "hard_conversation": (4, 4),
}


def validate_content() -> None:
    """Fail loudly at import/test time if the copy bank has a hole in it.

    Checks structural completeness only; tone and formatting are enforced
    separately in :mod:`.qa` against the *rendered* copy, because a fragment
    can be individually fine and still be wrong once blended.
    """
    problems: list[str] = []

    for type_id in range(1, 10):
        arch = ARCHETYPES.get(type_id)
        if arch is None:
            problems.append(f"Missing archetype for type {type_id}.")
            continue
        if arch.type_id != type_id:
            problems.append(f"Archetype at key {type_id} declares type_id {arch.type_id}.")
        for name, (lo, hi) in _REQUIRED_TUPLE_SIZES.items():
            value = getattr(arch, name)
            if not isinstance(value, tuple):
                problems.append(f"Type {type_id}.{name} is {type(value).__name__}, expected tuple.")
            elif not lo <= len(value) <= hi:
                problems.append(
                    f"Type {type_id}.{name} has {len(value)} items, expected {lo}-{hi}."
                )
        if arch.stress_to not in ARCHETYPES or arch.growth_to not in ARCHETYPES:
            problems.append(f"Type {type_id} points at a non-existent stress/growth type.")
        if arch.stress_to == type_id or arch.growth_to == type_id:
            problems.append(f"Type {type_id} points its stress/growth arrow at itself.")
        for trigger in arch.triggers:
            for attr in ("name", "looks_like", "why", "instead"):
                if not getattr(trigger, attr, "").strip():
                    problems.append(f"Type {type_id} trigger {trigger.name!r} has empty {attr}.")

    for slug in ("mom", "dad", "boyfriend", "girlfriend", "best-friend"):
        if slug not in LENSES:
            problems.append(f"Missing relationship lens for {slug!r}.")

    for kind in ("parent", "partner", "peer"):
        for type_id in range(1, 10):
            if not KIND_FRAMING.get((kind, type_id), "").strip():
                problems.append(f"Missing KIND_FRAMING for ({kind}, {type_id}).")

    if problems:
        raise ContentError(
            "Copy bank failed structural validation:\n" + "\n".join(f"  - {p}" for p in problems)
        )


def iter_templates() -> list[tuple[str, str]]:
    """Every authored string in the bank, labelled, for static template audit."""
    out: list[tuple[str, str]] = []

    def add(where: str, value) -> None:
        if isinstance(value, str):
            out.append((where, value))
        elif isinstance(value, tuple):
            for i, item in enumerate(value):
                add(f"{where}[{i}]", item)

    for type_id, arch in ARCHETYPES.items():
        prefix = f"type-{type_id}"
        for attr in (
            "one_line", "core_fear", "core_desire", "core_lie", "world_view", "gift",
            "friction", "stress_text", "growth_text", "tells", "deescalation", "repair",
            "repair_scripts", "boundary_scripts", "apology_to_them", "their_apology",
            "safe", "never", "starters", "hard_conversation", "daily_rhythm",
            "mistaken_for",
            "as_secondary", "pull",
        ):
            add(f"{prefix}.{attr}", getattr(arch, attr))
        for i, trigger in enumerate(arch.triggers):
            for attr in ("name", "looks_like", "why", "instead"):
                add(f"{prefix}.triggers[{i}].{attr}", getattr(trigger, attr))
        for attr in ("say", "never_say", "when_quiet", "when_angry", "green_flag",
                     "red_flag", "one_sentence"):
            add(f"{prefix}.cheat.{attr}", getattr(arch.cheat, attr))

    for slug, lens in LENSES.items():
        for attr in ("stakes", "power", "channel", "ask_form", "repair_window",
                     "history", "limits", "leverage"):
            add(f"lens-{slug}.{attr}", getattr(lens, attr))

    for (kind, type_id), text in KIND_FRAMING.items():
        add(f"kind-{kind}-{type_id}", text)

    for i, template in enumerate(TENSION_TEMPLATES):
        add(f"tension[{i}]", template)

    return out


def get_archetype(type_id: int) -> Archetype:
    """Fetch an archetype, with an error that says which lookup failed."""
    try:
        return ARCHETYPES[int(type_id)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ContentError(f"No archetype defined for type {type_id!r}.") from exc


def get_lens(slug: str) -> RelationshipLens:
    try:
        return LENSES[slug]
    except KeyError as exc:
        raise ContentError(f"No relationship lens defined for {slug!r}.") from exc
