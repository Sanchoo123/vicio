"""Configuração do robô: marcas, fontes e ritmos habituais de drop."""
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Lisbon")
# Nome honesto: o robô identifica-se sempre e não tenta passar por um browser.
USER_AGENT = "VicioDropCalendar/0.1 (calendario pessoal de drops)"

WINDOW_DAYS = 120        # só aceita datas até 120 dias no futuro
KEEP_PAST_DAYS = 60      # drops passados ficam para o histórico
MAX_PUSH_PER_RUN = 8     # nunca manda mais do que isto de uma vez
NTFY_MAX_DELAY_DAYS = 3  # o ntfy.sh só agenda avisos até 3 dias à frente

# match: expressões que identificam a marca no título/categorias de uma notícia.
# case=True quando a palavra é comum em inglês (Supreme, Palace, Represent).
BRANDS = {
    "supreme": dict(name="Supreme", site="https://eu.supreme.com", method="FCFS", case=True,
                    match=[r"\bSupreme\b(?!\s+(?:Court|Leader|Commander|Being|Council|Allied))"]),
    "palace": dict(name="Palace", site="https://www.palaceskateboards.com", method="FCFS", case=True,
                   match=[r"\bPalace Skateboards\b", r"(?<!Crystal )\bPalace\s+[xX]\s+\w", r"\w\s+[xX]\s+(?!Palace\s+(?:FC|Highlights)\b)Palace\b(?!\s*(?:FC|-))",
                          r"(?<!Crystal )\bPalace\s+(?:Spring|Summer|Autumn|Fall|Winter|Holiday|Ultimo|Drop)\b",
                          r"\bDropping at Palace\b", r"\bat Palace This Week\b"]),
    "stussy": dict(name="Stüssy", site="https://eu.stussy.com", method="FCFS", case=False,
                   match=[r"\bSt[üu]ssy\b"]),
    "corteiz": dict(name="Corteiz", site="https://www.crtz.xyz", method="FCFS", case=False,
                    match=[r"\bCorteiz\b", r"\bCRTZ\b"]),
    "brokenplanet": dict(name="Broken Planet", site="https://www.brokenplanet.com", method="FCFS", case=False,
                         match=[r"\bBroken Planet\b"]),
    "nike": dict(name="Nike", site="https://www.nike.com/pt/launch", method="SNKRS", case=False,
                 dated_only=True,  # há demasiadas notícias da Nike: só entram as que têm data de lançamento
                 match=[r"\bNike\b", r"\bAir Jordan\b", r"\bJordan Brand\b", r"\bSNKRS\b"]),
    "bape": dict(name="BAPE", site="https://bape.com", method="FCFS", case=False,
                 match=[r"\bBAPE\b", r"\bA BATHING APE\b"]),
    "represent": dict(name="Represent", site="https://representclo.com", method="FCFS", case=True,
                      match=[r"\bRepresent\s+(?:Clo|Owners Club|247|[xX])\b", r"\b[xX]\s+Represent\b", r"\bREPRESENT\b"]),
    "gallerydept": dict(name="Gallery Dept.", site="https://gallerydept.com", method="FCFS", case=False,
                        match=[r"\bGallery\s+Dept\b", r"\bGallery\s+Department\b"]),
    "fivefourfive": dict(name="FiveFourFive", site="https://fivefourfive.it", method="FCFS", case=False,
                         match=[r"\bFive\s?Four\s?Five\b", r"\b545\s?(?:merch|Milano)\b"]),
}

# Feeds públicos de notícias (RSS), feitos para serem lidos por programas.
FEEDS = [
    dict(name="Hypebeast", url="https://hypebeast.com/feed"),
    dict(name="Sneaker News", url="https://sneakernews.com/category/release-dates/feed/"),
    dict(name="Nice Kicks", url="https://www.nicekicks.com/feed/"),
    dict(name="Hypebeast Fashion", url="https://hypebeast.com/fashion/feed"),  # guarda 2 dias (o feed geral só ~6 h)
    dict(name="Sole Retriever", url="https://www.soleretriever.com/rss.xml"),
]

# Calendário oficial SNKRS Portugal (o mesmo que a página nike.com/pt/launch usa). Lido de hora a hora.
NIKE_FEED = ("https://api.nike.com/product_feed/threads/v3/?count=50&filter=marketplace(PT)&filter=language(pt-PT)"
             "&filter=upcoming(true)&filter=channelId(010794e5-35fe-4e32-aaff-cd2c74f89d61)"
             "&filter=exclusiveAccess(true,false)&sort=effectiveStartSellDateAsc")
NIKE_EVERY = 60

# Pesquisas no Google Notícias (feed RSS público): apanha os artigos de muitos sites sobre cada marca.
# Lido de hora a hora. Estas notícias aparecem na app mas não mandam aviso (há muitos artigos repetidos);
# as que trazem data de lançamento viram drops e esses sim avisam.
GNEWS_URL = "https://news.google.com/rss/search?hl=en-GB&gl=GB&ceid=GB:en&q="
GNEWS_EVERY = 60
GNEWS = [
    dict(brand="semana", q='"Everything Dropping at" when:7d'),  # listas semanais da Hypebeast (Supreme, Palace)
    dict(brand="supreme", q='Supreme (droplist OR "drop list" OR "week" OR collection OR collaboration) when:10d'),
    dict(brand="palace", q='"Palace Skateboards" OR "Palace x" OR "x Palace" when:14d'),
    dict(brand="stussy", q='Stussy OR Stüssy when:14d'),
    dict(brand="corteiz", q='Corteiz OR CRTZ when:14d'),
    dict(brand="brokenplanet", q='"Broken Planet" when:60d'),
    dict(brand="bape", q='BAPE OR "A Bathing Ape" when:14d'),
    dict(brand="represent", q='"Represent" (clothing OR "Owners Club" OR collection) when:30d'),
    dict(brand="gallerydept", q='"Gallery Dept" when:30d'),
    dict(brand="fivefourfive", q='FiveFourFive OR "545 merch" when:60d'),
]
GNEWS_KEEP_UNDATED = 4  # por marca e por ronda, para não encher as novidades com o mesmo assunto

# Lojas que deixam ler o catálogo público (products.json). As outras bloqueiam robôs
# (Supreme 403, Palace/Stüssy 429, Corteiz 401 com palavra-passe) e não as contornamos.
# every: de quantos em quantos minutos se pode ler a loja (o robô corre de 30 em 30; a BAPE limita pedidos).
STORES = [
    dict(brand="represent", url="https://representclo.com", currency="GBP", every=30),
    dict(brand="bape", url="https://bape.com", currency=None, every=60),
    dict(brand="gallerydept", url="https://gallerydept.com", currency="USD", every=60),
    dict(brand="fivefourfive", url="https://fivefourfive.it", currency="EUR", every=60),
]

# Ritmo habitual. Gera drops "previstos" até serem confirmados por notícias ou à mão.
# Datas das temporadas são aproximadas: ajusta quando as marcas anunciarem.
PATTERNS = [
    # Supreme: 11:00 de Nova Iorque, ao mesmo tempo no mundo todo (16:00 em Lisboa; 15:00 nas semanas em que
    # os EUA e a Europa mudam a hora em datas diferentes).
    dict(brand="supreme", weekday=3, time="11:00", tz="America/New_York", name="Drop semanal",
         seasons=[("2026-08-20", "2026-12-17"), ("2027-02-18", "2027-06-24")]),
    dict(brand="palace", weekday=4, time="11:00", tz="Europe/London", name="Drop semanal",
         seasons=[("2026-01-09", "2026-12-18"), ("2027-01-08", "2027-12-17")]),
]
PATTERN_DAYS_AHEAD = 21
