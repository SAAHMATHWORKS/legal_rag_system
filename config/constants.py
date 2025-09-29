from typing import Dict, List

# Country patterns for routing
COUNTRY_PATTERNS = {
    "benin": [
        r"\bbénin\b", r"\bbeninois\b", r"\bbéninoise\b", r"\bbenin\b",
        r"\bdahomey\b", r"\bporto-novo\b", r"\bcotonou\b",
        r"\bdroit béninois\b", r"\bloi béninoise\b"
    ],
    "madagascar": [
        r"\bmadagascar\b", r"\bmalgache\b", r"\bmalagasy\b",
        r"\bantananarivo\b", r"\bmadagasikara\b",
        r"\bdroit malgache\b", r"\bloi malgache\b"
    ]
}

# Article detection patterns
ARTICLE_PATTERNS = [
    r"article[s]?\s+(\d+(?:\s+(?:et|à|\-)\s+\d+)*)",
    r"art\.?\s*(\d+(?:\s+(?:et|à|\-)\s+\d+)*)",
    r"articles?\s+(\d+)\s*à\s*(\d+)",
    r"art\.?\s*(\d+)\s*au\s*(\d+)",
]

# Legal domain categories
CATEGORY_KEYWORDS = {
    "mariage": "Code des personnes et de la famille",
    "divorce": "Code des personnes et de la famille", 
    "héritage": "Code des personnes et de la famille",
    "succession": "Code des personnes et de la famille",
    "adoption": "Code des personnes et de la famille",
    "enfant": "Code des personnes et de la famille",
    "pension": "Code des personnes et de la famille",
    
    "infraction": "Droit pénal",
    "délit": "Droit pénal",
    "crime": "Droit pénal", 
    "peine": "Droit pénal",
    "prison": "Droit pénal",
    
    "entreprise": "Droit commercial",
    "commerce": "Droit commercial",
    "contrat": "Droit commercial",
    "société": "Droit commercial",
    
    "administration": "Droit administratif",
    "fonctionnaire": "Droit administratif",
    "service public": "Droit administratif"
}

# Document type detection keywords
DOCUMENT_TYPE_KEYWORDS = {
    "case_study": [
        "jurisprudence", "arrêt", "décision", "tribunal", "cours", "jugement",
        "affaire", "procès", "litige", "contentieux", "précédent", "cas",
        "cour d'appel", "cour suprême", "conseil d'état"
    ],
    "articles": [
        "article", "loi", "code", "décret", "texte", "disposition",
        "règlement", "ordonnance", "prescription", "norme"
    ]
}

# Document type descriptions
DOCUMENT_TYPE_DESCRIPTIONS = {
    "articles": "Textes législatifs et réglementaires (lois, codes, décrets)",
    "case_study": "Jurisprudence et décisions de justice (arrêts, jugements)"
}

# Legal context templates
LEGAL_CONTEXTS = {
    "benin": {
        "jurisdiction": "Bénin",
        "user_type": "citizen", 
        "document_type": "Code des personnes et de la famille",
        "language": "français",
        "legal_system": "civil_law"
    },
    "madagascar": {
        "jurisdiction": "Madagascar",
        "user_type": "citizen",
        "document_type": "legal", 
        "language": "français",
        "legal_system": "mixed_civil_customary"
    }
}

# User type contexts
USER_TYPE_CONTEXTS = {
    "citizen": {
        "expertise_level": "basic",
        "response_style": "accessible",
        "include_procedures": True
    },
    "lawyer": {
        "expertise_level": "advanced",
        "response_style": "technical", 
        "include_precedents": True
    },
    "student": {
        "expertise_level": "intermediate",
        "response_style": "educational",
        "include_examples": True
    }
}

# LAW_KEYWORDS a été supprimé comme demandé - le filtre "titre" n'est plus utilisé