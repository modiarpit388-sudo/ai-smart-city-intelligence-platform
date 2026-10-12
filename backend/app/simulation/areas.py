"""Static master data: 20 real Bengaluru localities with approximate coordinates and
urban characteristics that drive the synthetic data generators."""

ROAD_CODE = {"local": 0, "arterial": 1, "highway": 2, "junction": 3}
AREA_TYPE_CODE = {"residential": 0, "commercial": 1, "IT": 2, "industrial": 3, "mixed": 4}


def _a(name, lat, lng, pop, atype, road, tb, pb, ind, com, hist, aliases=""):
    return dict(
        name=name, slug=name.lower().replace(" ", "-"), lat=lat, lng=lng, population_k=pop,
        area_type=atype, road_type=road, traffic_base=tb, pollution_base=pb,
        industrial_index=ind, commercial_index=com, accident_hist=hist,
        has_junction=road == "junction", aliases=aliases,
    )


AREAS = [
    _a("Silk Board", 12.9177, 77.6233, 55, "commercial", "junction", .96, 1.10, .15, .75, 46, "silkboard,silk board junction"),
    _a("Electronic City", 12.8452, 77.6602, 85, "IT", "highway", .82, 1.00, .45, .70, 38, "e-city,ecity,electronic city phase"),
    _a("HSR Layout", 12.9116, 77.6474, 62, "residential", "arterial", .72, .95, .05, .55, 22, "hsr,h.s.r,hsr layout sector"),
    _a("Koramangala", 12.9352, 77.6245, 64, "commercial", "arterial", .85, 1.05, .05, .85, 30, "koramangla,kormangala"),
    _a("Whitefield", 12.9698, 77.7500, 110, "IT", "arterial", .80, 1.00, .30, .70, 31, "itpl,white field"),
    _a("Indiranagar", 12.9784, 77.6408, 48, "commercial", "arterial", .78, 1.02, .05, .85, 20, "indira nagar,100 feet road"),
    _a("Marathahalli", 12.9569, 77.7011, 72, "mixed", "junction", .90, 1.10, .20, .70, 40, "marathalli,marathahalli bridge"),
    _a("Hebbal", 13.0358, 77.5970, 58, "mixed", "highway", .88, 1.15, .25, .55, 44, "hebbal flyover"),
    _a("Jayanagar", 12.9250, 77.5938, 52, "residential", "local", .55, .85, .02, .60, 12, "jaya nagar"),
    _a("Malleshwaram", 13.0035, 77.5643, 45, "residential", "local", .58, .90, .05, .60, 14, "malleswaram,malleshwara"),
    _a("Yelahanka", 13.1007, 77.5963, 78, "residential", "highway", .50, .85, .15, .35, 18, "yelahanka new town"),
    _a("Bellandur", 12.9304, 77.6784, 68, "IT", "arterial", .86, 1.12, .25, .60, 33, "bellandur lake,orr bellandur"),
    _a("BTM Layout", 12.9166, 77.6101, 75, "residential", "arterial", .74, .98, .05, .55, 21, "btm,b.t.m"),
    _a("Majestic", 12.9767, 77.5713, 40, "commercial", "junction", .92, 1.25, .20, .95, 35, "kempegowda bus station,ksr,kbs"),
    _a("Banashankari", 12.9255, 77.5468, 66, "residential", "arterial", .60, .90, .05, .50, 15, "banashankri"),
    _a("Rajajinagar", 12.9982, 77.5530, 55, "mixed", "arterial", .65, .95, .20, .60, 17, "rajaji nagar"),
    _a("KR Puram", 13.0075, 77.6960, 62, "mixed", "junction", .88, 1.15, .25, .60, 37, "krishnarajapuram,k r puram,kr pura"),
    _a("Peenya", 13.0285, 77.5197, 50, "industrial", "arterial", .68, 1.30, .90, .40, 24, "peenya industrial area"),
    _a("Bannerghatta Road", 12.8930, 77.5975, 70, "mixed", "arterial", .70, .92, .10, .60, 19, "bannerghatta,bg road"),
    _a("MG Road", 12.9756, 77.6068, 30, "commercial", "arterial", .80, 1.00, .00, .95, 16, "mahatma gandhi road,brigade road"),
]
