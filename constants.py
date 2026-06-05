"""
Central constants for Emet Echo.

This helps deduplicate long lists that were scattered (APPROVED_SOURCES,
source type heuristics, etc.) and makes maintenance easier.
"""

# Conservative + independent news domains / url fragments used for filtering
# and "approved" classification.
# Keep this as the single source of truth.
APPROVED_SOURCES = [
    # Conservative news sources
    "foxnews.com",
    "nypost.com",
    "washingtontimes.com",
    "theepochtimes.com",
    "breitbart.com",
    "dailywire.com",
    "oann.com",
    "newsmax.com",
    "theblaze.com",
    "westernjournal.com",
    "dailycaller.com",
    "washingtonexaminer.com",
    "spectator.org",
    
    # Independent / heterodox
    "zerohedge.com",
    "reason.com",
    "thehill.com",
    "realclearpolitics.com",
    "axios.com",
    "theintercept.com",
    "justthenews.com",
    "substack.com",
    "ground.news",
    "breakingpoints.com",
    
    # Platforms / shows / substacks (expanded list)
    "rumble.com",
    "rumble.com/JovanHPulitzer",
    "rumble.com/c/DonaldJTrumpJr",
    "rumble.com/c/AndWeKnow",
    "tuckercarlson.com",
    "x.com/TuckerCarlson",
    "x.com/JovanHPulitzer",
    "x.com/laralogan",
    "laralogan.substack.com",
    "rwmalonemd.substack.com",
    "x.com/RWMaloneMD",
    "x.com/ScottWAtlas",
    "scottwalteratlas.substack.com",
    "twc.health",
    "x.com/RobertKennedyJr",
    "childrenshealthdefense.org",
    "bitchute.com",
    "gab.com",
    "banned.video",
    "frankspeech.com",
    "redvoicemedia.com",
    "thegatewaypundit.com",
    "redstate.com",
    "citizenfreepress.com",
    "100percentfedup.com",
    "emeralddb3.substack.com",
    "warroom.org",
    "1a3t.short.gy",
]

# Domains/fragments considered "conservative" for source_type tagging
# (used in ingestion to set Article.source_type)
CONSERVATIVE_SOURCE_FRAGMENTS = [
    "foxnews",
    "breitbart",
    "dailywire",
    "nypost",
    "washingtontimes",
    "theepochtimes",
]

# A few health / RFK specific domains used in rfk_jr route etc.
RFK_HEALTH_DOMAINS = [
    "childrenshealthdefense.org",
    "rwmalonemd.substack.com",
    "x.com/RWMaloneMD",
    "twc.health",
    "x.com/RobertKennedyJr",
]