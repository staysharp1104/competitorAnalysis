"""HTML结构化交互元素提取器"""
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

class HtmlStructExtractor:
    CHART_CLASS_PATTERNS = [re.compile(r"chart",re.I), re.compile(r"dashboard",re.I), re.compile(r"echarts|highcharts|chartjs",re.I), re.compile(r"plot|graph|visual",re.I)]
    CHART_TAG_IDS = re.compile(r"chart|dashboard|plot|graph|visualization|trend|stat", re.I)
    STAT_CARD_CLASSES = re.compile(r"stat|card|metric|indicator|summary|total|count|number", re.I)

    @staticmethod
    def extract_interactive_elements(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        elements = {"buttons": HtmlStructExtractor._extract_buttons(soup), "forms": HtmlStructExtractor._extract_forms(soup, url), "inputs": HtmlStructExtractor._extract_inputs(soup), "tables": HtmlStructExtractor._extract_tables(soup), "nav_links": HtmlStructExtractor._extract_links_nav(soup, url), "data_displays": HtmlStructExtractor._extract_data_displays(soup)}
        return {"page_type": HtmlStructExtractor.classify_page_type(elements, url), "total_interactive_elements": sum(len(v) for v in elements.values() if isinstance(v,list)), "interactive_elements": {k:v for k,v in elements.items() if v}}

    @staticmethod
    def _extract_buttons(soup):
        buttons = []
        for btn in soup.find_all("button"):
            text = btn.get_text(strip=True)
            if text or btn.get("onclick"): buttons.append({"text": text[:80], "type": btn.get("type","button"), "onclick": (btn.get("onclick","") or "")[:120]})
        for inp in soup.find_all("input", type=re.compile(r"button|submit|reset")):
            value = inp.get("value","") or inp.get("alt","") or ""
            if value: buttons.append({"text": value[:80], "type": "input-button"})
        for a in soup.find_all("a"):
            if any(kw in " ".join(a.get("class",[])).lower() for kw in ["btn","button","action"]):
                text = a.get_text(strip=True)
                if text: buttons.append({"text": text[:80], "type": "link-button", "href": a.get("href","")[:200]})
        return buttons

    @staticmethod
    def _extract_forms(soup, base_url):
        forms = []
        for form in soup.find_all("form"):
            fields = []
            for inp in form.find_all(["input","select","textarea"]):
                name = inp.get("name","") or inp.get("id","")
                inp_type = inp.get("type","text") if inp.name == "input" else inp.name
                if name and inp_type not in ("hidden","submit"): fields.append({"name": name[:60], "type": inp_type, "placeholder": (inp.get("placeholder","") or "")[:60]})
            action = form.get("action","")
            if action and not action.startswith(("http://","https://")): action = urljoin(base_url, action)
            forms.append({"action": action[:200], "method": form.get("method","get").upper(), "fields": fields, "field_count": len(fields)})
        return forms

    @staticmethod
    def _extract_inputs(soup):
        inputs = []
        for inp in soup.find_all("input"):
            inp_type = inp.get("type","text")
            if inp_type in ("hidden","submit","button","reset") or inp.find_parent("form"): continue
            name = inp.get("name","") or inp.get("id","")
            placeholder = inp.get("placeholder","") or ""
            if name or placeholder: inputs.append({"name": name[:60], "type": inp_type, "placeholder": placeholder[:60]})
        return inputs

    @staticmethod
    def _extract_tables(soup):
        tables = []
        for table in soup.find_all("table"):
            headers = []
            for th in table.find_all("th"): headers.append(th.get_text(strip=True)[:40])
            if not headers:
                for tr in table.find_all("tr"):
                    for th in tr.find_all("th"): headers.append(th.get_text(strip=True)[:40])
                    if headers: break
            tables.append({"id": (table.get("id","") or "")[:60], "columns": headers[:20], "column_count": len(headers), "estimated_rows": max(0,len(table.find_all("tr"))-(1 if headers else 0))})
        return tables

    @staticmethod
    def _extract_links_nav(soup, base_url):
        links = []; seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip(); text = a.get_text(strip=True)
            if not text or not href or href.startswith(("#","javascript:","mailto:")): continue
            if href.startswith("/"): href = urljoin(base_url, href)
            if href in seen: continue
            seen.add(href)
            links.append({"text": text[:80], "href": href[:200], "is_nav": bool(a.find_parent("nav")) or any(kw in " ".join(a.get("class",[])).lower() for kw in ["nav","menu","header","sidebar"])})
        return links

    @staticmethod
    def _extract_data_displays(soup):
        displays = []
        for el in soup.find_all(["div","canvas","svg"]):
            el_id = el.get("id","") or ""; el_class = " ".join(el.get("class",[]))
            for pattern in HtmlStructExtractor.CHART_CLASS_PATTERNS:
                if pattern.search(el_id) or pattern.search(el_class):
                    displays.append({"type": "chart_container", "tag": el.name, "id": el_id[:60]}); break
        for el in soup.find_all(["div","span","section"], class_=True):
            cls = " ".join(el.get("class",[]))
            if HtmlStructExtractor.STAT_CARD_CLASSES.search(cls):
                text = el.get_text(strip=True)[:100]
                if text: displays.append({"type": "stat_card", "text": text[:80]})
        return displays

    @staticmethod
    def classify_page_type(elements: dict, url: str = "") -> str:
        url_path = urlparse(url).path.lower()
        if any(kw in url_path for kw in ["/login","/signin","/register","/auth"]): return "auth_page"
        forms = elements.get("forms",[]); buttons = elements.get("buttons",[]); tables = elements.get("tables",[]); inputs = elements.get("inputs",[])
        if len(forms)+len(inputs)+len([b for b in buttons if b.get("type") in ("button","input-button")]) >= 5 and len(tables) >= 1: return "form_page"
        if len(tables) >= 1: return "data_table"
        if len(elements.get("data_displays",[])) >= 2: return "dashboard"
        if url_path.startswith("/settings") or url_path.startswith("/config"): return "settings_page"
        if len(elements.get("nav_links",[])) > 15: return "content_page"
        return "general_page"
