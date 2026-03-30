HISTORICAL_EO_DATA = {
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
        "key_themes": ["energy deregulation", "federal workforce reduction", "tax reform", "national security"],
        "milestones": {
            30: "Energy Emergency EO",
            45: "Federal hiring freeze",
            90: "Economic recovery orders",
        }
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
        "key_themes": ["economic stimulus", "healthcare policy", "NAFTA implementation", "environmental protection"],
        "milestones": {
            14: "Economic stimulus directives",
            60: "Healthcare task force orders",
            100: "100-day reform package",
        }
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
        "key_themes": ["financial regulation", "healthcare reform", "climate policy", "immigration"],
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
        "key_themes": ["immigration enforcement", "trade policy", "deregulation", "energy dominance"],
        "milestones": {
            7: "Travel ban EO",
            17: "Border wall directive",
            100: "Buy American, Hire American",
        }
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

