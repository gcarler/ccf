"""
Empirical stress-test suite for Obsidian-Style Knowledge Network.
Adversarial tests on:
- WikiLink parsing regex & edge cases (special chars, accents, question marks, nested brackets, unclosed tags)
- Duplicate links in single document
- Self links in documents
- Bidirectional backlink extraction and link counts
- Large-scale graph payload generation (0, 1, 500+ nodes) and performance
"""

import re
import time
from uuid import uuid4
from types import SimpleNamespace
import pytest
from backend.api.wiki import _normalize_page_key
from backend.schemas.wiki import WikiGraphNode, WikiGraphLink, WikiGraphData


def parse_wikilinks_from_content(content: str) -> set[str]:
    """Extracted core parsing logic identical to backend/api/wiki.py"""
    wiki_link_bracket_pattern = re.compile(r"\[\[(.*?)\]\]")
    wiki_link_tag_pattern = re.compile(r'data-page-key=["\']([^"\']+)["\']')
    wiki_link_href_pattern = re.compile(r'href=["\'][^"\']*/wiki/docs/([^"\'#?]+)["\']')

    targets = set()
    for match in wiki_link_bracket_pattern.findall(content or ""):
        target_str = match.split("|")[0].strip()
        if target_str:
            targets.add(target_str)

    for match in wiki_link_tag_pattern.findall(content or ""):
        target_str = match.strip()
        if target_str:
            targets.add(target_str)

    for match in wiki_link_href_pattern.findall(content or ""):
        target_str = match.strip()
        if target_str:
            targets.add(target_str)

    return targets


def build_graph_data_in_memory(pages: list[SimpleNamespace]) -> WikiGraphData:
    """Core graph builder identical to backend/api/wiki.py get_wiki_graph_data"""
    key_map = {}
    title_map = {}
    for p in pages:
        key_map[p.page_key] = p
        normalized_key = _normalize_page_key(p.page_key)
        key_map[normalized_key] = p
        if p.title:
            title_map[p.title.strip().lower()] = p.page_key

    nodes_dict = {
        p.page_key: WikiGraphNode(
            id=p.page_key,
            title=p.title,
            category=p.category or "General",
            links_count=0,
        )
        for p in pages
    }

    links_set = set()
    links_list: list[WikiGraphLink] = []

    wiki_link_bracket_pattern = re.compile(r"\[\[(.*?)\]\]")
    wiki_link_tag_pattern = re.compile(r'data-page-key=["\']([^"\']+)["\']')
    wiki_link_href_pattern = re.compile(r'href=["\'][^"\']*/wiki/docs/([^"\'#?]+)["\']')

    for page in pages:
        src = page.page_key
        content = page.content or ""
        targets_found = set()

        for match in wiki_link_bracket_pattern.findall(content):
            target_str = match.split("|")[0].strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str.lower() in title_map:
                targets_found.add(title_map[target_str.lower()])
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        for match in wiki_link_tag_pattern.findall(content):
            target_str = match.strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        for match in wiki_link_href_pattern.findall(content):
            target_str = match.strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        for tgt in targets_found:
            if tgt != src:
                link_key = (src, tgt)
                if link_key not in links_set:
                    links_set.add(link_key)
                    links_list.append(WikiGraphLink(source=src, target=tgt))
                    if src in nodes_dict:
                        nodes_dict[src].links_count += 1
                    if tgt in nodes_dict:
                        nodes_dict[tgt].links_count += 1

    return WikiGraphData(nodes=list(nodes_dict.values()), links=links_list)


def test_wikilink_bracket_standard_and_aliased():
    content = "Enlace a [[Doctrina Fundamental]] y también [[wiki_oracion|Guía de Oración]] y [[Pastoral]]."
    targets = parse_wikilinks_from_content(content)
    assert "Doctrina Fundamental" in targets
    assert "wiki_oracion" in targets
    assert "Pastoral" in targets


def test_wikilink_special_characters_and_punctuation():
    content = """
    Documento con enlaces difíciles:
    - [[Tema & Práctica: ¿Cómo orar?!]]
    - [[Versículo (Juan 3:16)]]
    - [[Guía #1 / 2026]]
    - [[¡Alabanza y Adoración!|Música]]
    """
    targets = parse_wikilinks_from_content(content)
    assert "Tema & Práctica: ¿Cómo orar?!" in targets
    assert "Versículo (Juan 3:16)" in targets
    assert "Guía #1 / 2026" in targets
    assert "¡Alabanza y Adoración!" in targets


def test_wikilink_html_tags_and_hrefs():
    content = """
    <p>Texto con enlace Tiptap <span data-type="wiki-link" data-page-key="wiki_liderazgo">Liderazgo</span></p>
    <p><a href="/plataforma/wiki/docs/wiki_evangelismo">Ir a Evangelismo</a></p>
    """
    targets = parse_wikilinks_from_content(content)
    assert "wiki_liderazgo" in targets
    assert "wiki_evangelismo" in targets


def test_wikilink_nested_brackets_and_malformed():
    content = "Anidado: [[Documento A [[Documento B]] ] ] y roto: [[Unclosed tag"
    targets = parse_wikilinks_from_content(content)
    # Non-greedy regex should capture "Documento A [[Documento B"
    assert len(targets) >= 1
    # Unclosed tag should NOT be matched
    assert not any("Unclosed" in t for t in targets)


def test_graph_payload_zero_nodes():
    graph = build_graph_data_in_memory([])
    assert graph.nodes == []
    assert graph.links == []


def test_graph_payload_single_isolated_node():
    page = SimpleNamespace(page_key="wiki_alone", title="Página Sola", category="General", content="Sin enlaces")
    graph = build_graph_data_in_memory([page])
    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "wiki_alone"
    assert graph.nodes[0].links_count == 0
    assert graph.links == []


def test_graph_duplicate_links_and_self_link_deduplication():
    """
    Document contains 50 duplicate references to [[wiki_target]] and a self-reference [[wiki_source]].
    Must produce:
    - 0 self-links
    - Exactly 1 directed link from wiki_source -> wiki_target
    - Correct links_count on both nodes
    """
    p1 = SimpleNamespace(
        page_key="wiki_source",
        title="Fuente",
        category="General",
        content=" ".join(["[[wiki_target]]"] * 50) + " [[wiki_source]] [[Fuente]]",
    )
    p2 = SimpleNamespace(
        page_key="wiki_target",
        title="Destino",
        category="Pastoral",
        content="Nada",
    )
    graph = build_graph_data_in_memory([p1, p2])
    assert len(graph.nodes) == 2
    assert len(graph.links) == 1
    assert graph.links[0].source == "wiki_source"
    assert graph.links[0].target == "wiki_target"

    nodes_by_id = {n.id: n for n in graph.nodes}
    assert nodes_by_id["wiki_source"].links_count == 1
    assert nodes_by_id["wiki_target"].links_count == 1


def test_graph_bidirectional_cyclic_links():
    """
    Page A links to Page B, Page B links to Page A.
    Must produce 2 distinct directed links: A -> B and B -> A.
    Both nodes must have links_count = 2.
    """
    p1 = SimpleNamespace(
        page_key="wiki_alpha",
        title="Alpha",
        category="Pastoral",
        content="Enlace hacia [[wiki_beta]]",
    )
    p2 = SimpleNamespace(
        page_key="wiki_beta",
        title="Beta",
        category="Doctrina",
        content="Enlace hacia [[Alpha]]",
    )
    graph = build_graph_data_in_memory([p1, p2])
    assert len(graph.nodes) == 2
    assert len(graph.links) == 2

    link_tuples = {(l.source, l.target) for l in graph.links}
    assert ("wiki_alpha", "wiki_beta") in link_tuples
    assert ("wiki_beta", "wiki_alpha") in link_tuples

    for n in graph.nodes:
        assert n.links_count == 2


def test_graph_large_scale_500_nodes_performance():
    """
    Generate 500 wiki pages with multiple cross-links.
    Verify execution time < 100ms and graph structure integrity.
    """
    N = 500
    pages = []
    for i in range(N):
        key = f"wiki_page_{i}"
        title = f"Documento Pastoral {i}"
        cat = ["Pastoral", "Doctrina", "Liderazgo", "Discipulado", "Operaciones"][i % 5]
        # Cross links to 3 subsequent pages and 1 predecessor
        links = []
        if i + 1 < N:
            links.append(f"[[wiki_page_{i+1}]]")
        if i + 2 < N:
            links.append(f"[[Documento Pastoral {i+2}]]")
        if i > 0:
            links.append(f"[[wiki_page_{i-1}]]")

        content = f"Contenido del doc {i}. " + " ".join(links)
        pages.append(SimpleNamespace(page_key=key, title=title, category=cat, content=content))

    start = time.perf_counter()
    graph = build_graph_data_in_memory(pages)
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(graph.nodes) == 500
    assert len(graph.links) > 1000
    assert duration_ms < 100, f"Graph generation exceeded 100ms: {duration_ms:.2f}ms"
