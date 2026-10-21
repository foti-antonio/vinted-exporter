#!/usr/bin/env python3
"""Esporta gli annunci visibili di un profilo Vinted (foto e testi).

Uso: python vinted_export.py https://www.vinted.it/member/123456-username
Richiede: pip install playwright && python -m playwright install chromium
Non aggira blocchi, CAPTCHA o pagine private.
"""

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:65] or "articolo"


def check_profile_url(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not re.fullmatch(r"(?:www\.)?vinted\.(?:[a-z]{2,3}|co\.uk)", host):
        raise argparse.ArgumentTypeError("Inserisci un URL https di un profilo Vinted.")
    if not re.match(r"^/member/\d+", parsed.path):
        raise argparse.ArgumentTypeError("Esempio: https://www.vinted.it/member/123456-nome")
    return value


def find_item_links(page) -> dict[str, str]:
    return page.evaluate("""() => {
      const primary = document.querySelectorAll(
        '[data-testid="grid-item"] a[href*="/items/"], [data-testid^="product-item-id-"] a[href*="/items/"]'
      );
      const anchors = primary.length ? primary : document.querySelectorAll('a[href*="/items/"]');
      const items = {};
      for (const a of anchors) {
        try {
          const u = new URL(a.href, location.origin);
          const m = u.pathname.match(/^\\/items\\/(\\d+)/);
          if (m && u.hostname === location.hostname) items[m[1]] = u.origin + u.pathname;
        } catch (_) {}
      }
      return items;
    }""")


def collect_links(page) -> dict[str, str]:
    found = {}
    no_growth = 0
    for _ in range(80):
        before = len(found)
        found.update(find_item_links(page))
        if len(found) != before:
            print(f"  Annunci individuati: {len(found)}", flush=True)
            no_growth = 0
        else:
            no_growth += 1

        # Vinted puo' caricare nuovi annunci scorrendo o con "Mostra altri".
        more = page.get_by_role(
            "button", name=re.compile(r"mostra altri|show more|load more|voir plus|mehr anzeigen", re.I)
        )
        clicked = False
        try:
            if more.count() and more.first.is_visible():
                more.first.click(timeout=2500)
                clicked = True
        except Exception:
            pass
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1800)
        if no_growth >= 5 and not clicked:
            break
    return found


def extract_item(page) -> dict:
    return page.evaluate("""() => {
      const text = sel => document.querySelector(sel)?.innerText?.trim() || '';
      const title = text('h1') || document.querySelector('meta[property="og:title"]')?.content || '';
      let product = null;
      for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
        try {
          const v = JSON.parse(s.textContent);
          const all = (Array.isArray(v) ? v : [v]).flatMap(x => x?.['@graph'] || [x]);
          const p = all.find(x => x && [x['@type']].flat().includes('Product'));
          if (p) { product = p; break; }
        } catch (_) {}
      }
      const candidates = [
        '[data-testid="item-description"]',
        '[data-testid="item-description-content"]',
        '[data-testid="item-page-description"]',
        '[data-testid="item-description-text"]',
        '[itemprop="description"]',
        '#item-description'
      ];
      let description = '';
      for (const sel of candidates) {
        const v = text(sel);
        if (v && v !== title) { description = v; break; }
      }
      if (!description && typeof product?.description === 'string') description = product.description;

      const hostOK = u => { try { return /^images\\d*\\.vinted\\.net$/.test(new URL(u).hostname); } catch (_) { return false; } };
      const bestSrc = img => {
        const srcset = img.getAttribute('srcset') || '';
        const candidates = srcset.split(',').map(x => x.trim().split(/\\s+/)[0]).filter(Boolean);
        return candidates.at(-1) || img.currentSrc || img.src || '';
      };
      const images = [...document.querySelectorAll('img')]
        .map(img => ({ url: bestSrc(img), alt: img.alt?.trim() || '', testid: img.getAttribute('data-testid') || '' }))
        .filter(x => hostOK(x.url));
      const wanted = title.trim().toLocaleLowerCase();
      let gallery = images.filter(x =>
        (wanted && x.alt.toLocaleLowerCase().startsWith(wanted) && /\\s+\\d+$/.test(x.alt)) ||
        /item-photo|item-image|item-gallery/i.test(x.testid)
      );
      if (!gallery.length) {
        const pimgs = [product?.image].flat().filter(Boolean)
          .map(x => typeof x === 'string' ? x : x.url || x.contentUrl || '')
          .filter(hostOK);
        gallery = pimgs.map(url => ({url, alt:'', testid:''}));
      }
      if (!gallery.length) {
        const og = document.querySelector('meta[property="og:image"]')?.content;
        if (og && hostOK(og)) gallery = [{url:og, alt:'', testid:''}];
      }
      // Le stesse foto possono comparire in miniatura e in grande: deduplica per ID dell'immagine.
      const seen = new Set();
      const urls = [];
      for (const x of gallery) {
        const path = new URL(x.url).pathname;
        const key = path.match(/\\/t\\/([^/]+)\\//)?.[1] || path;
        if (!seen.has(key)) { seen.add(key); urls.push(x.url); }
      }
      const brand = typeof product?.brand === 'string' ? product.brand : product?.brand?.name || '';
      const offers = Array.isArray(product?.offers) ? product.offers[0] : product?.offers;
      return {
        titolo: title, descrizione: description,
        prezzo: offers?.price ?? null, valuta: offers?.priceCurrency || null,
        marca: brand, urls_foto: urls.slice(0, 25)
      };
    }""")


def download_images(context, urls: list[str], folder: Path) -> tuple[list[str], list[str]]:
    saved, errors = [], []
    for i, url in enumerate(urls, 1):
        try:
            response = context.request.get(url, timeout=20000)
            if not response.ok:
                raise RuntimeError(f"HTTP {response.status}")
            content = response.body()
            ctype = response.headers.get("content-type", "").lower()
            if not ctype.startswith("image/") or len(content) > 25_000_000:
                raise ValueError("Contenuto non immagine o troppo grande")
            ext = ".webp" if "webp" in ctype else ".png" if "png" in ctype else ".jpg"
            name = f"{i:02d}{ext}"
            (folder / name).write_bytes(content)
            saved.append(name)
        except Exception as exc:
            errors.append(f"Foto {i}: {exc}")
    return saved, errors


def non_negative_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Inserisci un numero intero non negativo.") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("Il valore non può essere negativo.")
    return result


def non_negative_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Inserisci un numero non negativo.") from exc
    if not 0 <= result < float("inf"):
        raise argparse.ArgumentTypeError("Il valore deve essere finito e non negativo.")
    return result


def main():
    parser = argparse.ArgumentParser(description="Salva gli annunci pubblici di un profilo Vinted")
    parser.add_argument("profilo", type=check_profile_url, help="URL del profilo Vinted")
    parser.add_argument("--max", type=non_negative_int, default=0, help="Limita il numero di annunci (es. --max 5)")
    parser.add_argument("--output", default="vinted_export", help="Cartella di destinazione")
    parser.add_argument("--delay", type=non_negative_float, default=2.0,
                        help="Pausa in secondi fra annunci (default: 2)")
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(locale="it-IT", viewport={"width": 1300, "height": 900})
        page = context.new_page()
        try:
            page.goto(args.profilo, wait_until="domcontentloaded", timeout=45000)
            print("Browser aperto. Se compare un consenso cookie, gestiscilo manualmente.")
            input("Quando vedi gli annunci del profilo, premi INVIO qui nel terminale... ")
            links = collect_links(page)
            if not links:
                print("Nessun annuncio trovato. Controlla il profilo o un eventuale blocco Vinted.")
                return
            queue = list(links.items())[:args.max or None]
            print(f"\nTrovati {len(links)} annunci. Da esportare: {len(queue)}\n")
            index = []
            for number, (item_id, url) in enumerate(queue, 1):
                print(f"[{number}/{len(queue)}] {url}", flush=True)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(1200)
                    item = extract_item(page)
                    if not item["titolo"]:
                        raise RuntimeError("Titolo non disponibile: pagina non caricata o bloccata")
                    folder = root / f"{item_id}-{slugify(item['titolo'])}"
                    folder.mkdir(exist_ok=True)
                    # Esecuzioni successive riscaricano solo gli annunci incompleti.
                    state = folder / "prodotto.json"
                    if state.exists():
                        try:
                            existing = json.loads(state.read_text(encoding="utf-8"))
                            if existing.get("completo"):
                                index.append(existing)
                                print("  Gia' esportato, salto.")
                                continue
                        except (ValueError, OSError):
                            pass
                    images, errors = download_images(context, item["urls_foto"], folder)
                    item.update(id=item_id, url=url, foto=images, errori=errors)
                    # Non segnare completato un annuncio se manca la descrizione o una foto.
                    item["completo"] = bool(item["descrizione"] and images and not errors)
                    (folder / "descrizione.txt").write_text(
                        f"{item['titolo']}\n\n{item['descrizione']}\n\n{url}\n", encoding="utf-8"
                    )
                    state.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
                    index.append(item)
                    print(f"  {len(images)} foto; descrizione: {'OK' if item['descrizione'] else 'NON TROVATA'}")
                except Exception as exc:
                    print(f"  Errore: {exc}")
                time.sleep(args.delay)
            (root / "indice.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nFinito. File salvati in: {root}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
