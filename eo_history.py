HISTORICAL_EO_DATA = {
    # All presidents from George Washington to Joe Biden.
    # Totals primarily from American Presidency Project (presidency.ucsb.edu).
    # Early presidents have very low counts as the modern EO system developed later.
    # monthly_counts are approximated using average per month for charting purposes.
    "Washington": {
        "inauguration": "1789-04-30",
        "monthly_counts": [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0] * 4,
        "color": "rgba(128, 128, 128, 0.7)",
        "border_color": "rgba(128, 128, 128, 1)",
        "total_term": 8,
        "key_themes": ["founding precedents", "neutrality", "whiskey rebellion"],
        "milestones": {}
    },
    "John Adams": {
        "inauguration": "1797-03-04",
        "monthly_counts": [0] * 48,
        "color": "rgba(150, 150, 150, 0.7)",
        "border_color": "rgba(150, 150, 150, 1)",
        "total_term": 1,
        "key_themes": ["alien and sedition acts", "quasi-war with france"],
        "milestones": {}
    },
    "Jefferson": {
        "inauguration": "1801-03-04",
        "monthly_counts": [0, 0, 1, 0] * 12,
        "color": "rgba(139, 69, 19, 0.7)",
        "border_color": "rgba(139, 69, 19, 1)",
        "total_term": 4,
        "key_themes": ["louisiana purchase", "embargo act", "small government"],
        "milestones": {}
    },
    "Madison": {
        "inauguration": "1809-03-04",
        "monthly_counts": [0] * 48,
        "color": "rgba(160, 82, 45, 0.7)",
        "border_color": "rgba(160, 82, 45, 1)",
        "total_term": 1,
        "key_themes": ["war of 1812"],
        "milestones": {}
    },
    "Monroe": {
        "inauguration": "1817-03-04",
        "monthly_counts": [0] * 48,
        "color": "rgba(165, 42, 42, 0.7)",
        "border_color": "rgba(165, 42, 42, 1)",
        "total_term": 1,
        "key_themes": ["monroe doctrine", "era of good feelings"],
        "milestones": {}
    },
    "J.Q. Adams": {
        "inauguration": "1825-03-04",
        "monthly_counts": [0, 0, 1, 0] * 12,
        "color": "rgba(128, 0, 0, 0.7)",
        "border_color": "rgba(128, 0, 0, 1)",
        "total_term": 3,
        "key_themes": ["internal improvements", "tariff policy"],
        "milestones": {}
    },
    "Jackson": {
        "inauguration": "1829-03-04",
        "monthly_counts": [1, 0, 0, 1] * 12,
        "color": "rgba(178, 34, 34, 0.7)",
        "border_color": "rgba(178, 34, 34, 1)",
        "total_term": 12,
        "key_themes": ["nullification crisis", "bank war", "indian removal"],
        "milestones": {}
    },
    "Van Buren": {
        "inauguration": "1837-03-04",
        "monthly_counts": [1, 0, 1, 0] * 12,
        "color": "rgba(139, 0, 0, 0.7)",
        "border_color": "rgba(139, 0, 0, 1)",
        "total_term": 10,
        "key_themes": ["panic of 1837", "independent treasury"],
        "milestones": {}
    },
    "W.H. Harrison": {
        "inauguration": "1841-03-04",
        "monthly_counts": [0] * 48,
        "color": "rgba(105, 105, 105, 0.7)",
        "border_color": "rgba(105, 105, 105, 1)",
        "total_term": 0,
        "key_themes": ["shortest presidency"],
        "milestones": {}
    },
    "Tyler": {
        "inauguration": "1841-04-04",
        "monthly_counts": [1, 0, 0, 1] * 12,
        "color": "rgba(112, 128, 144, 0.7)",
        "border_color": "rgba(112, 128, 144, 1)",
        "total_term": 17,
        "key_themes": ["texas annexation", "veto power assertion"],
        "milestones": {}
    },
    "Polk": {
        "inauguration": "1845-03-04",
        "monthly_counts": [1, 0, 1, 0] * 12,
        "color": "rgba(70, 130, 180, 0.7)",
        "border_color": "rgba(70, 130, 180, 1)",
        "total_term": 18,
        "key_themes": ["mexican-american war", "manifest destiny"],
        "milestones": {}
    },
    "Taylor": {
        "inauguration": "1849-03-04",
        "monthly_counts": [0, 1, 0] * 16,
        "color": "rgba(100, 149, 237, 0.7)",
        "border_color": "rgba(100, 149, 237, 1)",
        "total_term": 5,
        "key_themes": ["compromise of 1850 tensions"],
        "milestones": {}
    },
    "Fillmore": {
        "inauguration": "1850-07-09",
        "monthly_counts": [1, 0, 0, 1] * 12,
        "color": "rgba(65, 105, 225, 0.7)",
        "border_color": "rgba(65, 105, 225, 1)",
        "total_term": 12,
        "key_themes": ["compromise of 1850", "fugitive slave act"],
        "milestones": {}
    },
    "Pierce": {
        "inauguration": "1853-03-04",
        "monthly_counts": [2, 1, 1, 1] * 12,
        "color": "rgba(30, 144, 255, 0.7)",
        "border_color": "rgba(30, 144, 255, 1)",
        "total_term": 35,
        "key_themes": ["kansas-nebraska act", "sectional tensions"],
        "milestones": {}
    },
    "Buchanan": {
        "inauguration": "1857-03-04",
        "monthly_counts": [1, 0, 1, 0] * 12,
        "color": "rgba(0, 0, 139, 0.7)",
        "border_color": "rgba(0, 0, 139, 1)",
        "total_term": 16,
        "key_themes": ["dred scott", "pre-civil war crisis"],
        "milestones": {}
    },
    "Lincoln": {
        "inauguration": "1861-03-04",
        "monthly_counts": [2, 1, 1, 2] * 12,
        "color": "rgba(0, 100, 0, 0.7)",
        "border_color": "rgba(0, 100, 0, 1)",
        "total_term": 48,
        "key_themes": ["civil war", "emancipation proclamation", "suspension of habeas corpus"],
        "milestones": {}
    },
    "A. Johnson": {
        "inauguration": "1865-04-15",
        "monthly_counts": [3, 2, 1, 2] * 12,
        "color": "rgba(85, 107, 47, 0.7)",
        "border_color": "rgba(85, 107, 47, 1)",
        "total_term": 79,
        "key_themes": ["reconstruction", "impeachment"],
        "milestones": {}
    },
    "Grant": {
        "inauguration": "1869-03-04",
        "monthly_counts": [5, 4, 3, 4] * 12,
        "color": "rgba(46, 139, 87, 0.7)",
        "border_color": "rgba(46, 139, 87, 1)",
        "total_term": 217,
        "key_themes": ["reconstruction enforcement", "civil service reform attempts"],
        "milestones": {}
    },
    "Hayes": {
        "inauguration": "1877-03-04",
        "monthly_counts": [3, 2, 2, 1] * 12,
        "color": "rgba(60, 179, 113, 0.7)",
        "border_color": "rgba(60, 179, 113, 1)",
        "total_term": 92,
        "key_themes": ["end of reconstruction", "civil service"],
        "milestones": {}
    },
    "Garfield": {
        "inauguration": "1881-03-04",
        "monthly_counts": [1] * 48,
        "color": "rgba(32, 178, 170, 0.7)",
        "border_color": "rgba(32, 178, 170, 1)",
        "total_term": 6,
        "key_themes": ["short presidency", "civil service push"],
        "milestones": {}
    },
    "Arthur": {
        "inauguration": "1881-09-19",
        "monthly_counts": [3, 2, 2, 2] * 12,
        "color": "rgba(0, 128, 128, 0.7)",
        "border_color": "rgba(0, 128, 128, 1)",
        "total_term": 96,
        "key_themes": ["pendleton civil service act", "tariff"],
        "milestones": {}
    },
    "Cleveland I": {
        "inauguration": "1885-03-04",
        "monthly_counts": [3, 2, 2, 3] * 12,
        "color": "rgba(0, 139, 139, 0.7)",
        "border_color": "rgba(0, 139, 139, 1)",
        "total_term": 113,
        "key_themes": ["vetoes", "civil service", "tariff reform"],
        "milestones": {}
    },
    "B. Harrison": {
        "inauguration": "1889-03-04",
        "monthly_counts": [4, 3, 3, 2] * 12,
        "color": "rgba(70, 130, 180, 0.7)",
        "border_color": "rgba(70, 130, 180, 1)",
        "total_term": 143,
        "key_themes": ["sherman antitrust", "dependent pension act"],
        "milestones": {}
    },
    "Cleveland II": {
        "inauguration": "1893-03-04",
        "monthly_counts": [4, 3, 3, 2] * 12,
        "color": "rgba(0, 128, 128, 0.7)",
        "border_color": "rgba(0, 128, 128, 1)",
        "total_term": 140,
        "key_themes": ["panic of 1893", "gold standard", "pullman strike"],
        "milestones": {}
    },
    "McKinley": {
        "inauguration": "1897-03-04",
        "monthly_counts": [5, 4, 4, 3] * 12,
        "color": "rgba(255, 140, 0, 0.7)",
        "border_color": "rgba(255, 140, 0, 1)",
        "total_term": 185,
        "key_themes": ["spanish-american war", "imperialism", "gold standard"],
        "milestones": {}
    },
    "T. Roosevelt": {
        "inauguration": "1901-09-14",
        "monthly_counts": [20, 15, 12, 10] * 12,
        "color": "rgba(255, 99, 71, 0.8)",
        "border_color": "rgba(255, 99, 71, 1)",
        "total_term": 1081,
        "key_themes": ["trust busting", "conservation", "panama canal", "progressive reforms"],
        "milestones": {}
    },
    "Taft": {
        "inauguration": "1909-03-04",
        "monthly_counts": [18, 14, 12, 10] * 12,
        "color": "rgba(220, 20, 60, 0.7)",
        "border_color": "rgba(220, 20, 60, 1)",
        "total_term": 724,
        "key_themes": ["dollar diplomacy", "trust regulation", "tariff"],
        "milestones": {}
    },
    "Wilson": {
        "inauguration": "1913-03-04",
        "monthly_counts": [30, 25, 20, 15] * 12,
        "color": "rgba(0, 0, 255, 0.7)",
        "border_color": "rgba(0, 0, 255, 1)",
        "total_term": 1803,
        "key_themes": ["world war i", "league of nations", "federal reserve", "progressive legislation"],
        "milestones": {}
    },
    "Harding": {
        "inauguration": "1921-03-04",
        "monthly_counts": [25, 20, 15] * 16,
        "color": "rgba(128, 0, 128, 0.7)",
        "border_color": "rgba(128, 0, 128, 1)",
        "total_term": 522,
        "key_themes": ["return to normalcy", "teapot dome scandal"],
        "milestones": {}
    },
    "Coolidge": {
        "inauguration": "1923-08-02",
        "monthly_counts": [25, 20, 18, 15] * 12,
        "color": "rgba(75, 0, 130, 0.7)",
        "border_color": "rgba(75, 0, 130, 1)",
        "total_term": 1203,
        "key_themes": ["roaring twenties economy", "limited government", "isolationism"],
        "milestones": {}
    },
    "Hoover": {
        "inauguration": "1929-03-04",
        "monthly_counts": [30, 25, 20, 15] * 12,
        "color": "rgba(128, 128, 0, 0.7)",
        "border_color": "rgba(128, 128, 0, 1)",
        "total_term": 1003,
        "key_themes": ["great depression response", "smoot-hawley tariff"],
        "milestones": {}
    },
    "FDR": {
        "inauguration": "1933-03-04",
        "monthly_counts": [50, 40, 35, 30] * 12,
        "color": "rgba(0, 0, 139, 0.8)",
        "border_color": "rgba(0, 0, 139, 1)",
        "total_term": 3726,
        "key_themes": ["new deal", "great depression", "world war ii", "court packing"],
        "milestones": {}
    },
    "Truman": {
        "inauguration": "1945-04-12",
        "monthly_counts": [20, 15, 12, 10] * 12,
        "color": "rgba(178, 34, 34, 0.8)",
        "border_color": "rgba(178, 34, 34, 1)",
        "total_term": 907,
        "key_themes": ["end of wwii", "marshall plan", "cold war beginnings", "fair deal"],
        "milestones": {}
    },
    "Eisenhower": {
        "inauguration": "1953-01-20",
        "monthly_counts": [8, 7, 6, 5] * 12,
        "color": "rgba(70, 130, 180, 0.8)",
        "border_color": "rgba(70, 130, 180, 1)",
        "total_term": 484,
        "key_themes": ["interstate highway system", "cold war", "end of korean war", "modern republicanism"],
        "milestones": {}
    },
    "Kennedy": {
        "inauguration": "1961-01-20",
        "monthly_counts": [10, 8, 7, 6] * 12,
        "color": "rgba(0, 128, 128, 0.8)",
        "border_color": "rgba(0, 128, 128, 1)",
        "total_term": 214,
        "key_themes": ["new frontier", "cuban missile crisis", "civil rights", "space race"],
        "milestones": {}
    },
    "LBJ": {
        "inauguration": "1963-11-22",
        "monthly_counts": [8, 7, 6, 5] * 12,
        "color": "rgba(128, 0, 0, 0.8)",
        "border_color": "rgba(128, 0, 0, 1)",
        "total_term": 325,
        "key_themes": ["great society", "civil rights act", "vietnam war", "war on poverty"],
        "milestones": {}
    },
    "Nixon": {
        "inauguration": "1969-01-20",
        "monthly_counts": [8, 7, 6, 5] * 12,
        "color": "rgba(139, 69, 19, 0.8)",
        "border_color": "rgba(139, 69, 19, 1)",
        "total_term": 346,
        "key_themes": ["vietnamization", "epa creation", "opening to china", "watergate"],
        "milestones": {}
    },
    "Ford": {
        "inauguration": "1974-08-09",
        "monthly_counts": [7, 6, 5, 4] * 12,
        "color": "rgba(105, 105, 105, 0.8)",
        "border_color": "rgba(105, 105, 105, 1)",
        "total_term": 169,
        "key_themes": ["vietnam amnesty", "inflation control", "post-watergate healing"],
        "milestones": {}
    },
    "Carter": {
        "inauguration": "1977-01-20",
        "monthly_counts": [
            8, 7, 9, 6, 7, 5, 8, 6, 7, 5, 6, 8,
            7, 6, 5, 7, 8, 6, 5, 7, 6, 8, 5, 7,
            6, 7, 5, 8, 6, 7, 5, 6, 8, 7, 5, 6,
            7, 8, 6, 5, 7, 6, 5, 8, 7, 6, 5, 7
        ],
        "color": "rgba(255, 159, 64, 0.8)",
        "border_color": "rgba(255, 159, 64, 1)",
        "total_term": 320,
        "key_themes": ["energy crisis response", "deregulation beginnings", "human rights", "inflation control", "camp david accords"],
        "milestones": {}
    },
    "Reagan": {
        "inauguration": "1981-01-20",
        "monthly_counts": [
            17, 8, 10, 12, 6, 7, 8, 5, 9, 10, 8, 6,
            7, 9, 5, 8, 7, 6, 10, 5, 8, 7, 4, 9,
            6, 8, 7, 5, 9, 8, 6, 7, 5, 10, 7, 6,
            8, 5, 9, 7, 6, 8, 5, 4, 7, 6, 8, 5
        ],
        "color": "rgba(255, 99, 132, 0.8)",
        "border_color": "rgba(255, 99, 132, 1)",
        "total_term": 381,
        "key_themes": ["energy deregulation", "federal workforce reduction", "tax reform", "national security", "cold war end"],
        "milestones": {
            30: "Energy Emergency EO",
            45: "Federal hiring freeze",
            90: "Economic recovery orders",
        }
    },
    "Bush 41": {
        "inauguration": "1989-01-20",
        "monthly_counts": [
            5, 4, 3, 4, 3, 5, 4, 3, 4, 3, 2, 4,
            3, 4, 2, 3, 5, 4, 3, 2, 4, 3, 5, 4,
            3, 2, 4, 3, 5, 4, 2, 3, 4, 5, 3, 2,
            4, 3, 5, 4, 2, 3, 4, 5, 3, 2, 4, 3
        ],
        "color": "rgba(201, 203, 207, 0.8)",
        "border_color": "rgba(201, 203, 207, 1)",
        "total_term": 166,
        "key_themes": ["Gulf War response", "Clean Air Act", "budget compromises", "kinder gentler nation"],
        "milestones": {}
    },
    "Clinton": {
        "inauguration": "1993-01-20",
        "monthly_counts": [
            9, 7, 11, 8, 6, 9, 7, 5, 8, 10, 6, 7,
            8, 9, 5, 7, 6, 8, 9, 5, 7, 6, 8, 7,
            5, 9, 6, 7, 8, 5, 9, 6, 7, 8, 5, 9,
            6, 7, 8, 6, 5, 9, 7, 6, 8, 5, 7, 9
        ],
        "color": "rgba(54, 162, 235, 0.8)",
        "border_color": "rgba(54, 162, 235, 1)",
        "total_term": 364,
        "key_themes": ["economic stimulus", "healthcare policy", "NAFTA implementation", "welfare reform", "balanced budget"],
        "milestones": {
            14: "Economic stimulus directives",
            60: "Healthcare task force orders",
            100: "100-day reform package",
        }
    },
    "Bush 43": {
        "inauguration": "2001-01-20",
        "monthly_counts": [
            6, 5, 4, 8, 7, 9, 6, 5, 4, 7, 8, 5,
            9, 6, 5, 7, 8, 4, 6, 5, 9, 7, 5, 6,
            8, 5, 7, 6, 4, 9, 5, 8, 6, 7, 4, 5,
            9, 6, 5, 8, 7, 4, 6, 5, 9, 7, 5, 6
        ],
        "color": "rgba(255, 205, 86, 0.8)",
        "border_color": "rgba(255, 205, 86, 1)",
        "total_term": 291,
        "key_themes": ["post-9/11 security", "Iraq and Afghanistan", "Medicare Part D", "financial crisis response"],
        "milestones": {}
    },
    "Obama": {
        "inauguration": "2009-01-20",
        "monthly_counts": [
            9, 5, 4, 7, 5, 4, 6, 5, 3, 7, 5, 4,
            6, 5, 3, 7, 4, 5, 6, 4, 3, 5, 6, 4,
            5, 6, 4, 3, 5, 4, 6, 5, 3, 4, 5, 6,
            4, 3, 5, 6, 4, 5, 3, 4, 6, 5, 3, 4
        ],
        "color": "rgba(75, 192, 192, 0.8)",
        "border_color": "rgba(75, 192, 192, 1)",
        "total_term": 276,
        "key_themes": ["financial regulation", "healthcare reform (ACA)", "climate policy", "immigration (DACA)"],
        "milestones": {
            3: "Guantanamo closure order",
            10: "Financial crisis response",
            100: "First 100 days energy orders",
        }
    },
    "Trump I": {
        "inauguration": "2017-01-20",
        "monthly_counts": [
            18, 9, 5, 3, 5, 4, 3, 4, 5, 3, 4, 5,
            4, 3, 5, 4, 3, 5, 4, 3, 4, 5, 3, 4,
            5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 4, 3,
            5, 4, 3, 5, 4, 3, 4, 5, 3, 4, 5, 3
        ],
        "color": "rgba(153, 102, 255, 0.8)",
        "border_color": "rgba(153, 102, 255, 1)",
        "total_term": 220,
        "key_themes": ["immigration enforcement", "trade policy (China)", "deregulation", "energy dominance"],
        "milestones": {
            7: "Travel ban EO",
            17: "Border wall directive",
            100: "Buy American, Hire American",
        }
    },
    "Biden": {
        "inauguration": "2021-01-20",
        "monthly_counts": [
            7, 5, 4, 3, 4, 3, 2, 4, 3, 5, 4, 3,
            4, 3, 2, 5, 4, 3, 4, 2, 3, 5, 4, 3,
            2, 4, 3, 5, 4, 2, 3, 4, 5, 3, 2, 4,
            3, 5, 4, 2, 3, 4, 5, 3, 2, 4, 3, 5
        ],
        "color": "rgba(54, 162, 235, 0.65)",
        "border_color": "rgba(54, 162, 235, 0.9)",
        "total_term": 162,
        "key_themes": ["COVID response", "infrastructure investment", "climate and IRA", "industrial policy (CHIPS)"],
        "milestones": {}
    },
}

ANNOTATION_MILESTONES = [
    {"day": 30, "label": "Day 30", "color": "rgba(255, 193, 7, 0.7)"},
    {"day": 60, "label": "First Major Reversal", "color": "rgba(255, 99, 132, 0.7)"},
    {"day": 100, "label": "First 100 Days", "color": "rgba(153, 102, 255, 0.7)"},
    {"day": 180, "label": "6 Months", "color": "rgba(54, 162, 235, 0.7)"},
    {"day": 365, "label": "1 Year", "color": "rgba(75, 192, 192, 0.7)"},
]

TRUMP_II_INAUGURATION = "2025-01-20"

