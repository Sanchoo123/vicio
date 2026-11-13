import unittest
from datetime import date, datetime

from robot import ics
from robot.config import TZ
from robot.run import allowed, build_messages, merge, reminders
from robot.sources import patterns, rss, shopify
from robot.text import detect_brand, find_date, find_time

TODAY = date(2026, 11, 12)


class Dates(unittest.TestCase):
    def test_date_in_title(self):
        self.assertEqual(find_date("The Reebok G-Unit G6 Is Dropping Again On November 20th", TODAY), date(2026, 11, 20))

    def test_ignores_updated_stamp(self):
        txt = "Updated November 11th, 2026: Following a sell-out, it returns December 5th."
        self.assertEqual(find_date(txt, TODAY), date(2026, 12, 5))

    def test_next_year(self):
        self.assertEqual(find_date("Air Jordan 1 releases Jan. 9", TODAY), date(2027, 1, 9))

    def test_old_and_far_dates_rejected(self):
        self.assertIsNone(find_date("Originally released March 3rd, 2019", TODAY))
        self.assertIsNone(find_date("Coming October 2nd", TODAY))  # passado e a mais de 120 dias

    def test_may_as_verb(self):
        self.assertIsNone(find_date("Nike may 20 percent off", TODAY))

    def test_time_converted_to_lisbon(self):
        self.assertEqual(find_time("Releasing 10 a.m. ET", date(2026, 11, 20)), (date(2026, 11, 20), "15:00"))
        self.assertEqual(find_time("drops at 11am GMT", date(2026, 11, 20)), (date(2026, 11, 20), "11:00"))


class Brands(unittest.TestCase):
    def test_brands(self):
        self.assertEqual(detect_brand("Supreme Fall/Winter 2026 Week 12 Droplist"), "supreme")
        self.assertIsNone(detect_brand("Supreme Court rules on tariffs"))
        self.assertIsNone(detect_brand("Inside Buckingham Palace"))
        self.assertIsNone(detect_brand("Crystal Palace x Liverpool - Highlights"))
        self.assertIsNone(detect_brand("Crystal Palace Drop Into Relegation Zone"))
        self.assertEqual(detect_brand("Burberry x Palace"), "palace")
        self.assertEqual(detect_brand("Palace Skateboards Winter 2026 Lookbook"), "palace")
        self.assertEqual(detect_brand("Stüssy x Nike Air Force 1 Releases November 20th"), "stussy")
        self.assertEqual(detect_brand("Corteiz Drops Alcatraz Bomber"), "corteiz")
        self.assertEqual(detect_brand("Air Jordan 4 \"Spotlight\" Releases December 6th"), "nike")
        self.assertIsNone(detect_brand("These colors represent the season"))


FEED = b"""<?xml version="1.0"?><rss><channel>
<item><title>Air Jordan 11 "Gamma" Releases December 12th</title><link>https://ex.com/aj11</link>
<guid>g1</guid><pubDate>Thu, 12 Nov 2026 10:00:00 +0000</pubDate><category>Release Dates</category>
<description>&lt;p&gt;&lt;img src="https://ex.com/images/kicksfinder-logo.svg"/&gt;&lt;img src="https://img.ex/aj11.jpg"/&gt;Out at 10 a.m. ET.&lt;/p&gt;</description></item>
<item><title>Where To Buy The Nike Air Bakin</title><link>https://ex.com/bakin</link><guid>g2</guid></item>
<item><title>Supreme Fall/Winter 2026 Week 13 Droplist</title><link>https://ex.com/sup</link><guid>g3</guid>
<pubDate>Wed, 18 Nov 2026 12:00:00 +0000</pubDate><description>&lt;img src="https://img.ex/sup.jpg"&gt;</description></item>
<item><title>Netflix new show</title><link>https://ex.com/n</link><guid>g4</guid></item>
</channel></rss>"""


class Feed(unittest.TestCase):
    def test_parse(self):
        items = rss.parse_feed(FEED, "Teste", TODAY)
        self.assertEqual([i["brand"] for i in items], ["nike", "supreme"])  # Nike sem data e Netflix ficam de fora
        aj = items[0]
        self.assertEqual((aj["date"], aj["time"], aj["image"]), ("2026-12-12", "15:00", "https://img.ex/aj11.jpg"))
        self.assertTrue(items[1]["droplist"])
        d = rss.to_drop(aj)
        self.assertTrue(d["id"].startswith("nike-2026-12-12-air-jordan-11"))
        self.assertEqual(d["status"], "confirmado")


GNEWS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Corteiz x Nike Shox R419 \xe2\x80\x9cMetallic Silver\xe2\x80\x9d Launches On November 20th - Sneaker News</title>
<link>https://news.google.com/rss/articles/abc</link><guid>gn1</guid><pubDate>Wed, 11 Nov 2026 15:00:00 GMT</pubDate>
<description>&lt;a href="x"&gt;Corteiz x Nike Shox R419&lt;/a&gt;</description><source url="https://sneakernews.com">Sneaker News</source></item>
<item><title>Palace Skateboards Opens London Flagship - Culted</title><link>https://news.google.com/rss/articles/def</link>
<guid>gn2</guid><source url="https://culted.com">Culted</source></item>
</channel></rss>"""


class GoogleNews(unittest.TestCase):
    def test_parse(self):
        a, b = rss.parse_feed(GNEWS, "Google Notícias", TODAY, gnews=True)
        self.assertEqual((a["brand"], a["date"], a["source"]), ("corteiz", "2026-11-20", "Sneaker News"))
        self.assertFalse(a["title"].endswith("Sneaker News"))
        self.assertIsNone(a["image"])
        d = rss.to_drop(a)
        self.assertEqual((d["id"], d["name"]), ("corteiz-2026-11-20", "Corteiz x Nike Shox R419 \u201cMetallic Silver\u201d"))
        self.assertEqual((b["brand"], b["source"], b.get("date")), ("palace", "Culted", None))


class Patterns(unittest.TestCase):
    def test_weekly(self):
        now = datetime(2026, 11, 12, 9, 0, tzinfo=TZ)
        ex = {d["id"]: d for d in patterns.expected(now)}
        self.assertIn("supreme-2026-11-19", ex)
        self.assertEqual(ex["palace-2026-11-13"]["time"], "11:00")
        self.assertEqual(ex["supreme-2026-11-19"]["time"], "16:00")  # 11:00 em Nova Iorque
        self.assertTrue(all(d["status"] == "previsto" for d in ex.values()))


class Merge(unittest.TestCase):
    def test_priority_and_sources(self):
        a = dict(id="x", origin="pattern", date="2026-11-19", time="11:00", status="previsto", image=None,
                 products=[], sources=[dict(name="Ritmo", url="u1")])
        b = dict(id="x", origin="manual", date="2026-11-19", time=None, status="confirmado", image="i",
                 products=[], sources=[dict(name="Mão", url="u2")])
        (m,) = merge([b, a])
        self.assertEqual((m["status"], m["time"], m["image"], m["origin"]), ("confirmado", "11:00", "i", "manual"))
        self.assertEqual(len(m["sources"]), 2)


class Store(unittest.TestCase):
    def test_new_products_and_restock(self, ):
        store = dict(brand="represent", url="https://shop", currency="GBP")
        p = lambda i, h, av: dict(id=i, title=f"P{i}", handle=h, variants=[dict(price="100.00", available=av)], images=[dict(src=f"img{i}")])
        calls = [dict(products=[p(1, "a", False)]),
                 dict(products=[p(1, "a", True), p(2, "b", True), p(3, "c", True)])]
        shopify.get_json = lambda url: calls.pop(0)
        st, now = {}, datetime(2026, 11, 12, 18, 0, tzinfo=TZ)
        drop, ev = shopify.check_store(store, st, ["a"], now)
        self.assertIsNone(drop)
        self.assertEqual(ev, [])  # primeira leitura não avisa
        drop, ev = shopify.check_store(store, st, ["a"], now)
        self.assertEqual([e["type"] for e in ev], ["store_new", "restock"])
        self.assertEqual(len(drop["products"]), 2)
        self.assertEqual(drop["products"][0]["price"], 100.0)


class Notify(unittest.TestCase):
    me = dict(avisos_por_marca=dict(nike="meus", corteiz="tudo", bape="nada"), vou_entrar={"nike-x": {"pecas": ["AJ11"]}})

    def test_levels(self):
        self.assertFalse(allowed(self.me, "new_drop", "nike", False))
        self.assertTrue(allowed(self.me, "changed", "nike", True))
        self.assertTrue(allowed(self.me, "news", "corteiz", False))
        self.assertFalse(allowed(self.me, "news", "stussy", False))  # padrão 'drops'
        self.assertFalse(allowed(self.me, "restock", "bape", False))

    def test_reminders_scheduled_once(self):
        d = dict(id="nike-x", brand="nike", name="AJ11", date="2026-11-13", time="08:00", sources=[dict(name="s", url="u")])
        st, now = {}, datetime(2026, 11, 12, 20, 0, tzinfo=TZ)
        msgs = reminders([d], self.me, st, now)
        self.assertEqual(len(msgs), 2)
        self.assertIn("1. AJ11", msgs[0]["message"])
        self.assertEqual(reminders([d], self.me, st, now), [])

    def test_cap(self):
        d = dict(id="c", brand="corteiz", name="n", date="2026-11-20", time=None, sources=[dict(name="s", url="u")])
        msgs = build_messages([dict(type="new_drop", drop=d)] * 20, self.me)
        self.assertEqual(len(msgs), 8)
        self.assertIn("E mais 13", msgs[-1]["title"])


class Calendar(unittest.TestCase):
    def test_ics(self):
        d = dict(id="palace-2026-11-13", brand="palace", name="Drop semanal", date="2026-11-13", time="11:00",
                 status="previsto", method="FCFS", sources=[dict(name="Ritmo", url="https://p")])
        out = ics.build([d], "Teste", alarms=True)
        self.assertIn("DTSTART:20261113T110000Z", out)
        self.assertIn("TRIGGER:-PT10M", out)
        self.assertTrue(all(len(l.encode()) <= 75 for l in out.split("\r\n")))


if __name__ == "__main__":
    unittest.main()
