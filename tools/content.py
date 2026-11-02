"""Single source of truth for the profile README.

Edit the copy here, then run `python tools/build.py` to regenerate
README.md, README.pt-BR.md and every SVG in assets/.

Copy mirrors portfolio-bk/src/data (profile.ts, projects.ts).
"""

from __future__ import annotations

# Same palette as the portfolio: black/white/grey base, each project keeps its own colour.
# Colour is a signal (squares, arrows, bands), never a gradient or glow.
COLORS = {
    "talos": "#ef5f67",
    "rotor": "#7aa2f7",
    "prazinho": "#2fc68a",
    "rigor": "#e9a23b",
    "rr": "#a683d8",
}

# Text colours per GitHub theme. Backgrounds stay transparent so the SVGs sit on GitHub's own page colour.
THEMES = {
    "dark": {"fg": "#eeeeec", "mute": "#9a9a96", "faint": "#74746f", "line": "#2b2b2b", "ink": "#0b0b0b", "inv": "#0b0b0b"},
    "light": {"fg": "#0b0b0b", "mute": "#62625e", "faint": "#8f8f8a", "line": "#e2e2de", "ink": "#0b0b0b", "inv": "#eeeeec"},
}

REPO = "https://github.com/bk-marcosr/bk-marcosr"
PROFILE = "https://github.com/bk-marcosr"
PORTFOLIO = "https://bk-marcosr.github.io/portfolio-bk/"
EMAIL = "marcosgabriel20061216@gmail.com"
LINKEDIN = "https://www.linkedin.com/in/marcos-gabriel-rodrigues-ba%C3%ADa-0181022a5/"

NAME = "Marcos Gabriel"

# Featured projects: language-independent fields.
PROJECTS = [
    {
        "slug": "rotor",
        "name": "Rotor",
        "year": "2025—26",
        "stack": ["React", "TypeScript", "Supabase", "PostgreSQL", "Vault", "Edge Functions", "Binance API"],
    },
    {
        "slug": "prazinho",
        "name": "Prazinho",
        "year": "2026",
        "stack": ["React", "TypeScript", "Tailwind", "shadcn/ui", "Supabase", "Vitest", "Vercel"],
    },
    {
        "slug": "talos",
        "name": "Talos",
        "year": "2026",
        "stack": ["Node.js", "Express", "Baileys", "Gemini", "Next.js", "React Flow", "Supabase", "Stripe"],
    },
    {
        "slug": "rigor",
        "name": "Rigor",
        "year": "2026",
        "stack": ["Python", "SQLite", "Supabase", "React", "TypeScript"],
    },
]

OTHER_PROJECTS = [
    {"name": "BK Flow"},
    {"name": "Pleno Movimento"},
    {"name": "AgendaLink"},
    {"name": "OrçaPro"},
    {"name": "BK Echo"},
    {"name": "CVM Extract", "url": "https://github.com/bk-marcosr/CVM_extract"},
]

# Ledger colours: "fg" is the inverted band (paper on dark, ink on light), like BKode on the portfolio.
EXPERIENCE = [
    {"org": "RR Chevrolet", "color": "rr"},
    {"org": "BKode", "color": "fg"},
    {"org": "UTIC", "color": "rotor"},
    {"org": "UFRA", "color": "prazinho"},
]

LANGS = {
    "en": {
        "readme": "README.md",
        "html_lang": "en",
        "hero": {
            "location": ["Belém, Pará", "Brazil · UTC−3"],
            "role": ["Full stack", "developer"],
            "alt": "Marcos Gabriel — full stack developer in Belém, Pará, Brazil (UTC−3).",
        },
        "about": {
            "label": "About",
            "tokens": [
                ("text", "I’m Marcos, a full stack dev in Belém. I automate data at"),
                ("underline", "RR Chevrolet", "rr"),
                ("text", "and ship products that handle real money"),
                ("pill", "rotor"),
                ("pill", "prazinho"),
                ("text", "and talk to real customers"),
                ("pill", "talos"),
                ("glue", "."),
            ],
        },
        "work": {
            "title": "Selected work",
            "aside": "Live projects, real interfaces",
            "projects": {
                "rotor": {
                    "category": "Real-money trading",
                    "line": "Trading bot running real money on Binance. Live since September 2026.",
                },
                "prazinho": {
                    "category": "Financial management",
                    "line": "Installment sales, inventory and month-end close for small resellers.",
                },
                "talos": {
                    "category": "AI customer service",
                    "line": "WhatsApp customer service with AI, for small businesses.",
                },
                "rigor": {
                    "category": "B3 & CVM data",
                    "line": "Fifteen years of CVM filings turned into twelve indicators per B3-listed company.",
                },
            },
        },
        "also": {
            "title": "Also built",
            "tag": "open source",
            "note": "Most repositories are private. Happy to walk you through the code on a call.",
            "items": {
                "BK Flow": "Editorial calendar, approval and Instagram publishing for agencies.",
                "Pleno Movimento": "Pilates studio management: students, classes, schedule, payments and a student portal.",
                "AgendaLink": "Scheduling for independent professionals, with Stripe payments.",
                "OrçaPro": "PDF quotes for freelancers and small business owners.",
                "BK Echo": "Audio transcription and AI document generation, with human approval.",
                "CVM Extract": "Financial statement extraction from CVM filings.",
            },
        },
        "ledger": {
            "label": "Where I am",
            "items": {
                "RR Chevrolet": {
                    "period": "2026 — now",
                    "role": "Automation & Data",
                    "description": "Rocketbot and Python bots that export CRM events, match them against the ad leads spreadsheet and deliver a dashboard and KPI report. I restructured the bots into an orchestrator with isolated modules and fixed the reconciliation window, cutting about 92% of false positives.",
                },
                "BKode": {
                    "period": "2024 — now",
                    "role": "Founder, developer",
                    "description": "My own products and systems for clients: AI customer service on WhatsApp, management for a pilates studio, scheduling with payments and the finance SaaS products.",
                },
                "UTIC": {
                    "period": "2026 — now",
                    "role": "Administrative & Finance Director",
                    "description": "UFRA’s IT junior enterprise. I run the financial structure and the resource allocation policy.",
                },
                "UFRA": {
                    "period": "in progress",
                    "role": "Information Systems",
                    "description": "Federal Rural University of the Amazon, Belém.",
                },
            },
        },
        "stack": {
            "label": "Day to day",
            "tools": [
                "TypeScript", "JavaScript", "Python", "SQL",
                "React", "Next.js", "Vite", "Tailwind", "TanStack Query",
                "Node.js", "Express", "Zod", "Prisma", "Supabase Edge Functions",
                "PostgreSQL with RLS", "Redis", "BullMQ", "SQLite",
                "Vitest", "Playwright", "Docker Compose", "GitHub Actions", "Vercel",
                "Stripe", "Binance", "Meta Graph", "WhatsApp", "Gemini", "OpenAI",
            ],
        },
        "contact": {
            "title": ["Let’s", "talk?"],
            "links": {"linkedin": "LinkedIn", "portfolio": "Portfolio", "email": "E-mail"},
        },
        "switch": {"en": "English", "pt": "Português"},
        "footer": "Belém, PA · Colors taken from the projects themselves.",
    },
    "pt": {
        "readme": "README.pt-BR.md",
        "html_lang": "pt-BR",
        "hero": {
            "location": ["Belém, Pará", "Brasil · UTC−3"],
            "role": ["Desenvolvedor", "full stack"],
            "alt": "Marcos Gabriel — desenvolvedor full stack em Belém, Pará, Brasil (UTC−3).",
        },
        "about": {
            "label": "Sobre",
            "tokens": [
                ("text", "Sou o Marcos, dev full stack em Belém. Automatizo dados na"),
                ("underline", "RR Chevrolet", "rr"),
                ("text", "e coloco no ar produto que mexe com dinheiro"),
                ("pill", "rotor"),
                ("pill", "prazinho"),
                ("text", "e com cliente"),
                ("pill", "talos"),
                ("text", "de verdade."),
            ],
        },
        "work": {
            "title": "Trabalhos selecionados",
            "aside": "Projetos no ar, interface real",
            "projects": {
                "rotor": {
                    "category": "Trading com dinheiro real",
                    "line": "Robô de trading com dinheiro real na Binance. Operando desde setembro de 2026.",
                },
                "prazinho": {
                    "category": "Gestão financeira",
                    "line": "Venda a prazo, estoque e fechamento do mês para pequeno revendedor.",
                },
                "talos": {
                    "category": "Atendimento com IA",
                    "line": "Atendimento no WhatsApp com IA, para pequenas empresas.",
                },
                "rigor": {
                    "category": "Dados da B3 e CVM",
                    "line": "Quinze anos de balanços da CVM viram doze indicadores por empresa da B3.",
                },
            },
        },
        "also": {
            "title": "Também construí",
            "tag": "código aberto",
            "note": "A maioria dos repositórios é privada. Mostro o código numa conversa.",
            "items": {
                "BK Flow": "Calendário editorial, aprovação e publicação no Instagram para agências.",
                "Pleno Movimento": "Gestão de studio de pilates: alunos, aulas, agenda, pagamentos e portal do aluno.",
                "AgendaLink": "Agendamento para autônomos com pagamento pelo Stripe.",
                "OrçaPro": "Orçamento em PDF para freelancer e MEI.",
                "BK Echo": "Transcrição de áudio e geração de documento com IA, com aprovação humana.",
                "CVM Extract": "Extração de demonstrações financeiras da CVM.",
            },
        },
        "ledger": {
            "label": "Onde estou",
            "items": {
                "RR Chevrolet": {
                    "period": "2026 — hoje",
                    "role": "Automação & Dados",
                    "description": "Robôs em Rocketbot e Python que exportam eventos do CRM, cruzam com a planilha de leads dos anúncios e entregam dashboard e relatório de KPI. Reorganizei os robôs em orquestrador e módulos isolados e corrigi a janela de conciliação, cortando cerca de 92% dos falsos positivos.",
                },
                "BKode": {
                    "period": "2024 — hoje",
                    "role": "Fundador, desenvolvedor",
                    "description": "Produtos próprios e sistemas para clientes: atendimento com IA no WhatsApp, a gestão de um studio de pilates, agendamento com pagamento e os SaaS financeiros.",
                },
                "UTIC": {
                    "period": "2026 — hoje",
                    "role": "Diretor Administrativo-Financeiro",
                    "description": "Empresa júnior de TI da UFRA. Cuido da estrutura financeira e da política de alocação de recursos.",
                },
                "UFRA": {
                    "period": "em curso",
                    "role": "Sistemas de Informação",
                    "description": "Universidade Federal Rural da Amazônia, Belém.",
                },
            },
        },
        "stack": {
            "label": "No dia a dia",
            "tools": [
                "TypeScript", "JavaScript", "Python", "SQL",
                "React", "Next.js", "Vite", "Tailwind", "TanStack Query",
                "Node.js", "Express", "Zod", "Prisma", "Supabase Edge Functions",
                "PostgreSQL com RLS", "Redis", "BullMQ", "SQLite",
                "Vitest", "Playwright", "Docker Compose", "GitHub Actions", "Vercel",
                "Stripe", "Binance", "Meta Graph", "WhatsApp", "Gemini", "OpenAI",
            ],
        },
        "contact": {
            "title": ["Vamos", "conversar?"],
            "links": {"linkedin": "LinkedIn", "portfolio": "Portfólio", "email": "E-mail"},
        },
        "switch": {"en": "English", "pt": "Português"},
        "footer": "Belém, PA · Cores tiradas dos próprios projetos.",
    },
}
