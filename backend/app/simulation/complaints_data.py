"""Synthetic citizen-complaint corpus (category + priority labelled) used to train the NLP models."""
import random

from .areas import AREAS

DURATIONS_LOW = ["a couple of days", "since yesterday", "this week"]
DURATIONS_MED = ["the last three days", "over five days", "several days now"]
DURATIONS_HIGH = ["more than a week", "over ten days", "nearly two weeks", "the past 15 days"]

# category -> priority -> templates.  {loc} = locality, {dur} = duration phrase
T = {
    "Garbage": {
        "LOW": ["The garbage bin near {loc} bus stop is a bit untidy, please get it cleaned when possible.",
                "Slight littering on the footpath in {loc} for {dur}, kindly send someone to sweep.",
                "Waste bin at the park in {loc} needs to be emptied soon.",
                "Requesting a dustbin at the corner of our lane in {loc}."],
        "MEDIUM": ["Garbage has been dumped near our apartment in {loc} for {dur} and nobody is collecting it.",
                   "Waste collection truck did not come to our street in {loc} for {dur}.",
                   "Overflowing dustbins and scattered plastic waste in {loc} for {dur}, very frustrating.",
                   "Garbage is piling up beside the road in {loc}, please arrange collection."],
        "HIGH": ["Huge pile of rotting garbage in {loc} for {dur}, terrible smell and a health hazard for children!",
                 "Urgent: garbage dump is on fire near homes in {loc}, thick smoke spreading, dangerous.",
                 "Rotting waste is attracting stray dogs and rats in {loc} for {dur}, disease risk, please act immediately.",
                 "Medical waste dumped openly near the school in {loc}, this is dangerous and unsafe."],
    },
    "Roads": {
        "LOW": ["There is a small crack on the road near {loc} market, please repair when possible.",
                "Road marking has faded near the signal in {loc}, needs repainting.",
                "Footpath tiles are loose in front of the mall in {loc}.",
                "Minor bump on the road in {loc}, kindly level it."],
        "MEDIUM": ["Big potholes on the main road in {loc} for {dur}, vehicles are struggling.",
                   "The road in {loc} is badly damaged after rain and traffic is slow for {dur}.",
                   "Broken road edge and gravel on the lane in {loc}, please resurface.",
                   "Repeated complaints about potholes in {loc}, nothing done for {dur}."],
        "HIGH": ["Deep pothole on the flyover in {loc} caused an accident, a biker was injured, urgent repair needed!",
                 "Road has caved in near {loc} and is extremely dangerous for vehicles, please act immediately.",
                 "Massive open pit in the middle of the road in {loc} with no barricade, dangerous at night.",
                 "Several bikers fell in the potholes at {loc} for {dur}, serious injuries, emergency repair needed."],
    },
    "Water": {
        "LOW": ["Water pressure is slightly low in the morning in {loc}.",
                "Please check the water meter in our building in {loc}, reading seems off.",
                "Water supply timing in {loc} changed, kindly confirm the schedule.",
                "Requesting a new water connection for our house in {loc}."],
        "MEDIUM": ["No water supply in our street in {loc} for {dur}, tankers are expensive.",
                   "Dirty brownish water is coming from the tap in {loc} for {dur}.",
                   "Water pipe is leaking on the road in {loc}, water being wasted for {dur}.",
                   "Irregular water supply in {loc} for {dur}, please fix the pumping issue."],
        "HIGH": ["No drinking water at all in {loc} for {dur}, elderly people and children suffering, urgent!",
                 "Contaminated sewage-smelling water supplied in {loc}, many residents fell sick, emergency.",
                 "Main water pipeline burst in {loc}, road flooded and houses affected, immediate action required.",
                 "Hospital in {loc} has no water supply since morning, this is critical."],
    },
    "Electricity": {
        "LOW": ["Electricity bill for our flat in {loc} looks slightly higher than usual, please review.",
                "Requesting a new meter installation in {loc}.",
                "Voltage fluctuates a little in the evenings in {loc}.",
                "Please trim the tree branches touching the power line in {loc} when convenient."],
        "MEDIUM": ["Frequent power cuts in {loc} for {dur}, work from home is affected.",
                   "No electricity in our block in {loc} for several hours every day for {dur}.",
                   "Transformer in {loc} is humming loudly and the power keeps tripping for {dur}.",
                   "Low voltage in {loc} damaging appliances, complaint pending for {dur}."],
        "HIGH": ["Live wire hanging on the road in {loc} after the rain, extremely dangerous, please act immediately!",
                 "Transformer is sparking and smoking in {loc}, fire risk near homes, emergency.",
                 "Complete blackout in {loc} for {dur}, hospital and elderly patients affected, urgent.",
                 "Electric pole is leaning dangerously near the school in {loc}, may fall any time."],
    },
    "Traffic": {
        "LOW": ["Please add a zebra crossing near the school in {loc}.",
                "The signal timing at {loc} junction could be optimised a bit.",
                "Need a speed breaker sign board at the lane in {loc}.",
                "Suggest a bus shelter near {loc} for commuters."],
        "MEDIUM": ["Heavy traffic jams at {loc} every evening for {dur}, please deploy traffic police.",
                   "Illegal parking is blocking the road in {loc} for {dur}, causing congestion.",
                   "Traffic signal at {loc} is not working properly for {dur}, long queues.",
                   "Vehicles are going wrong way near {loc}, causing frequent jams."],
        "HIGH": ["Traffic signal is completely dead at {loc} junction and vehicles are colliding, dangerous, send police now!",
                 "Ambulance stuck in massive jam at {loc}, gridlock for hours, urgent intervention needed.",
                 "Rash driving and racing near {loc} school has caused near accidents, unsafe for children.",
                 "Accident blocked the whole road at {loc}, injured people on the road, please help immediately."],
    },
    "Street lights": {
        "LOW": ["One street light is flickering near {loc} park.",
                "Street light pole in our lane in {loc} needs repainting.",
                "Requesting an additional light at the corner in {loc}.",
                "The street light timer in {loc} switches on a bit late."],
        "MEDIUM": ["Street lights are not working on our road in {loc} for {dur}, very dark at night.",
                   "Several lights are off along the main road in {loc} for {dur}, please repair.",
                   "Dark stretch near the bus stop in {loc} for {dur}, commuters uncomfortable.",
                   "Street lights burn during the day and are off at night in {loc}."],
        "HIGH": ["Complete darkness on the road in {loc} for {dur}, chain snatching happened, women feel unsafe, urgent!",
                 "Street light pole fell on the road in {loc} and is dangerous, wires exposed.",
                 "No lights around the underpass in {loc}, multiple accidents at night, immediate action needed.",
                 "Broken street light with live wires near children's playground in {loc}, dangerous."],
    },
    "Drainage": {
        "LOW": ["Roadside drain in {loc} needs routine cleaning.",
                "Small blockage in the storm water drain near {loc} shop.",
                "Please clean the manhole cover area in {loc}.",
                "Drain slab is slightly broken in our lane in {loc}."],
        "MEDIUM": ["Blocked drain in {loc} for {dur}, dirty water stagnating on the street.",
                   "Sewage water is overflowing near houses in {loc} for {dur}, bad smell.",
                   "Rain water is not draining from the road in {loc} for {dur}.",
                   "Mosquito breeding in the stagnant drain in {loc} for {dur}."],
        "HIGH": ["Sewage overflowing into homes in {loc} for {dur}, health hazard, disease spreading, urgent!",
                 "Open manhole without cover in {loc}, a child almost fell in, dangerous, emergency.",
                 "Severe flooding in {loc} as drains are choked, water entering houses, immediate help needed.",
                 "Drain burst and sewage flooding the main road near hospital in {loc}, critical."],
    },
    "Pollution": {
        "LOW": ["There is some dust from a small construction near {loc}.",
                "Mild smell from the lake area in {loc} in the evenings.",
                "Please plant more trees along the road in {loc} to reduce pollution.",
                "Loud music in the neighbourhood of {loc} during the weekend."],
        "MEDIUM": ["Thick smoke from a factory chimney in {loc} for {dur}, breathing is difficult.",
                   "Construction dust and noise in {loc} for {dur}, no water sprinkling.",
                   "Burning of leaves and plastic in the open in {loc} for {dur}, air smells bad.",
                   "Vehicles emitting black smoke on the main road in {loc}, air quality is poor."],
        "HIGH": ["Toxic fumes from an industrial unit in {loc} for {dur}, residents coughing, hospital visits, urgent!",
                 "Foam and chemical smell from the lake in {loc}, fish dying and air unbearable, dangerous.",
                 "Illegal burning of tyres near homes in {loc}, thick black smoke, children with breathing problems, emergency.",
                 "Gas leak smell in {loc}, people feel dizzy, immediate action required."],
    },
    "Public safety": {
        "LOW": ["The park gate in {loc} is left unlocked at night.",
                "Requesting a CCTV camera at the market entrance in {loc}.",
                "Stray dogs are gathering near {loc} lane, please have them checked.",
                "Missing signage for the emergency exit at the mall in {loc}."],
        "MEDIUM": ["Frequent bike thefts reported in {loc} for {dur}, please increase patrolling.",
                   "Drunk people creating nuisance outside the bar in {loc} for {dur}.",
                   "Stray dog menace in {loc}, several people bitten in {dur}.",
                   "Unauthorised hawkers blocking the footpath in {loc}, pedestrians unsafe."],
        "HIGH": ["Women harassed near the bus stop in {loc} at night, unsafe, need police immediately!",
                 "Fire in a building in {loc}, people trapped, please send fire brigade now, emergency.",
                 "Gang fight and violence on the street in {loc}, injured people, urgent police help.",
                 "Suspicious person threatening residents in {loc}, dangerous situation, please act immediately."],
    },
}

PREFIX = ["", "", "", "Hello, ", "Dear sir, ", "Kindly note: ", "Complaint: ", "Sir/Madam, "]
SUFFIX = ["", "", "", " Please take action.", " Kindly look into it.", " Thank you.", " This is very frustrating.",
          " We are disappointed with the delay.", " Request a quick response.", " Awaiting your reply."]


def _loc_phrase(rng):
    a = rng.choice(AREAS)
    names = [a["name"]] + [x.strip() for x in a["aliases"].split(",") if x.strip()][:1]
    return rng.choice(names) if rng.random() < 0.35 else a["name"]


# ---------------------------------------------------------------- compositional generator
# Builds many additional, differently-worded complaints from (subject, problem, context) parts so the
# classifiers learn vocabulary instead of memorising a handful of sentences.
V = {
    "Garbage": (["garbage", "waste", "trash", "rubbish", "litter", "dustbin", "garbage dump", "pile of waste"],
                ["is not being collected", "has been dumped openly", "is piling up", "is overflowing", "is scattered everywhere",
                 "smells terrible", "is rotting"]),
    "Roads": (["pothole", "road", "footpath", "speed breaker", "flyover surface", "asphalt", "road edge"],
              ["is badly damaged", "has deep cracks", "is broken", "has caved in", "is full of potholes", "is uneven",
               "needs resurfacing"]),
    "Water": (["water supply", "tap water", "water pipeline", "drinking water", "water tanker", "water meter", "borewell"],
              ["has stopped", "is dirty", "is leaking", "has very low pressure", "is contaminated", "is irregular", "has not come"]),
    "Electricity": (["power supply", "electricity", "transformer", "electric pole", "power line", "electricity meter", "voltage"],
                    ["is cut frequently", "has failed", "is sparking", "is fluctuating", "has tripped repeatedly",
                     "is very low", "is not restored"]),
    "Traffic": (["traffic signal", "traffic jam", "junction", "parking", "bus stop", "road crossing", "vehicles"],
                ["is not working", "is blocked for hours", "is chaotic", "is causing long queues", "is jammed",
                 "has no traffic police", "is unmanaged"]),
    "Street lights": (["street light", "lamp post", "road lighting", "light pole", "street lamp", "lights on the road"],
                      ["is not working", "is flickering", "is switched off", "has been broken", "stays off at night",
                       "is very dim", "is missing"]),
    "Drainage": (["drain", "sewage", "manhole", "storm water drain", "sewer line", "gutter", "drain water"],
                 ["is blocked", "is overflowing", "is stagnating", "has burst", "smells bad", "is open", "is choked"]),
    "Pollution": (["smoke", "air pollution", "dust", "industrial fumes", "noise", "burning waste", "chemical smell"],
                  ["is unbearable", "is spreading", "is making breathing difficult", "is coming from the factory",
                   "is very high", "is harming residents", "is constant"]),
    "Public safety": (["theft", "stray dogs", "harassment", "fighting", "suspicious people", "fire", "unlit lane"],
                      ["is happening often", "is scaring residents", "needs police patrol", "is unsafe for women",
                       "has increased", "is threatening children", "is out of control"]),
}
CONTEXTS = ["near our apartment", "on the main road", "outside the school", "behind the market", "beside the park",
            "at the corner of our street", "near the bus stop", "opposite the temple", "close to the hospital"]
CUES = {
    "LOW": ["It is a minor issue.", "No hurry, but please look into it.", "Just a small problem.",
            "Whenever possible please fix it.", "Mild inconvenience only."],
    "MEDIUM": ["This has been going on for {dur}.", "Please fix this soon.", "It is causing inconvenience to residents.",
               "Nobody has responded so far.", "We have complained before."],
    "HIGH": ["This is dangerous!", "It is an emergency, act immediately.", "Health hazard for children and elders.",
             "People have been injured.", "Extremely urgent, please respond now."],
}


def _compose(cat, pri, rng, dur):
    subj, prob = V[cat]
    s, p, c = rng.choice(subj), rng.choice(prob), rng.choice(CONTEXTS)
    loc = _loc_phrase(rng)
    form = rng.randrange(3)
    if form == 0:
        core = f"{s.capitalize()} {p} {c} in {loc}."
    elif form == 1:
        core = f"In {loc}, the {s} {p} {c}."
    else:
        core = f"Problem at {loc}: {s} {p}."
    return core + " " + rng.choice(CUES[pri]).format(dur=dur)


def _noise(text, rng):
    """Mimic real-world messy text: dropped words and typos."""
    words = text.split()
    if len(words) > 8 and rng.random() < 0.30:
        del words[rng.randrange(len(words))]
    if rng.random() < 0.20:
        i = rng.randrange(len(words))
        w = words[i]
        if len(w) > 4:
            j = rng.randrange(1, len(w) - 2)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def make_complaints(n: int = 1600, seed: int = 7, noisy: bool = True):
    rng = random.Random(seed)
    cats = list(T.keys())
    rows = []
    for i in range(n):
        cat = cats[i % len(cats)]
        pri = rng.choices(["LOW", "MEDIUM", "HIGH"], weights=[0.28, 0.44, 0.28])[0]
        dur = rng.choice({"LOW": DURATIONS_LOW, "MEDIUM": DURATIONS_MED, "HIGH": DURATIONS_HIGH}[pri])
        if rng.random() < 0.5:  # compositional sentence (tpl = -1)
            tpl_i = -1
            text = rng.choice(PREFIX) + _compose(cat, pri, rng, dur) + rng.choice(SUFFIX)
        else:
            tpl_i = rng.randrange(len(T[cat][pri]))
            text = rng.choice(PREFIX) + T[cat][pri][tpl_i].format(loc=_loc_phrase(rng), dur=dur) + rng.choice(SUFFIX)
        text = _noise(text.strip(), rng) if noisy else text.strip()
        if noisy and rng.random() < 0.03:  # small amount of label noise, like real annotators
            pri = rng.choice(["LOW", "MEDIUM", "HIGH"])
        rows.append({"text": text, "category": cat, "priority": pri, "tpl": tpl_i})
    rng.shuffle(rows)
    return rows
